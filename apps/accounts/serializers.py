from urllib.parse import urlencode
from datetime import timedelta
from secrets import randbelow
from smtplib import SMTPException

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import SignupVerificationCode

User = get_user_model()


SIGNUP_CODE_TTL_MINUTES = 5
SIGNUP_CODE_MAX_ATTEMPTS = 5


class EmailDeliveryError(Exception):
    pass


def _generate_signup_code():
    return f"{randbelow(1000000):06d}"


def send_signup_verification_code(email):
    clean_email = email.strip().lower()
    code = _generate_signup_code()
    now = timezone.now()
    verification = SignupVerificationCode.objects.create(
        email=clean_email,
        code_hash=make_password(code),
        expires_at=now + timedelta(minutes=SIGNUP_CODE_TTL_MINUTES),
    )
    try:
        send_mail(
            "Your Droptop signup code",
            (
                "Use this code to finish creating your Droptop account:\n\n"
                f"{code}\n\n"
                "This code expires in 5 minutes. If you did not request it, you can ignore this email."
            ),
            settings.DEFAULT_FROM_EMAIL,
            [clean_email],
            fail_silently=False,
        )
    except (SMTPException, OSError, TimeoutError) as exc:
        verification.delete()
        raise EmailDeliveryError("Signup verification email could not be sent.") from exc

    SignupVerificationCode.objects.filter(
        email__iexact=clean_email,
        consumed_at__isnull=True,
    ).exclude(pk=verification.pk).update(consumed_at=now)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "business_name",
            "phone_number",
            "profile_photo_url",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
        ]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name", "business_name", "phone_number"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def save(self, **kwargs):
        send_signup_verification_code(self.validated_data["email"])
        return None


class RegisterVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    business_name = serializers.CharField(required=False, allow_blank=True, max_length=255)
    phone_number = serializers.CharField(required=False, allow_blank=True, max_length=50)

    default_error_messages = {
        "invalid_code": "Invalid or expired verification code.",
        "too_many_attempts": "Too many failed attempts. Request a new code.",
    }

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        email = attrs["email"]
        verification = SignupVerificationCode.objects.filter(
            email__iexact=email,
            consumed_at__isnull=True,
        ).order_by("-created_at").first()

        if not verification or verification.is_expired:
            self.fail("invalid_code")
        if verification.attempts >= SIGNUP_CODE_MAX_ATTEMPTS:
            self.fail("too_many_attempts")
        if not check_password(attrs["code"], verification.code_hash):
            verification.attempts += 1
            verification.save(update_fields=["attempts"])
            self.fail("invalid_code")

        attrs["verification"] = verification
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        verification = self.validated_data["verification"]
        email = self.validated_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError({"email": "An account with this email already exists."})

        user = User.objects.create_user(
            email=email,
            password=self.validated_data["password"],
            first_name=self.validated_data.get("first_name", ""),
            last_name=self.validated_data.get("last_name", ""),
            business_name=self.validated_data.get("business_name", ""),
            phone_number=self.validated_data.get("phone_number", ""),
        )
        verification.consumed_at = timezone.now()
        verification.save(update_fields=["consumed_at"])
        return user


class LoginSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        user = authenticate(request=self.context.get("request"), email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        refresh = self.get_token(user)
        return {"refresh": str(refresh), "access": str(refresh.access_token), "user": UserSerializer(user).data}


class GoogleAuthSerializer(serializers.Serializer):
    credential = serializers.CharField()
    intent = serializers.ChoiceField(choices=["login", "signup"], required=False, default="login")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, **kwargs):
        email = self.validated_data["email"].strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return None

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_token = f"{uid}:{token}"
        reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?{urlencode({'token': reset_token})}"

        try:
            send_mail(
                "Reset your Droptop password",
                (
                    "We received a request to reset your Droptop password.\n\n"
                    f"Open this link to choose a new password:\n{reset_url}\n\n"
                    "This link expires in 1 hour. If you did not request this, you can ignore this email."
                ),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except (SMTPException, OSError, TimeoutError) as exc:
            raise EmailDeliveryError("Password reset email could not be sent.") from exc
        return user


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8)

    default_error_messages = {
        "invalid_token": "Invalid or expired password reset token.",
    }

    def validate(self, attrs):
        raw_token = attrs["token"].strip()
        try:
            uidb64, reset_token = raw_token.split(":", 1)
            user_id = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            self.fail("invalid_token")

        if not default_token_generator.check_token(user, reset_token):
            self.fail("invalid_token")

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["password"])
        user.save(update_fields=["password"])
        return user


class EmailTokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
