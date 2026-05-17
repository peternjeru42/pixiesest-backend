from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


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
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "email", "is_active", "date_joined", "last_login", "created_at", "updated_at"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "password", "first_name", "last_name", "business_name", "phone_number"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)


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

        send_mail(
            "Reset your Droptop password",
            (
                "We received a request to reset your Droptop password.\n\n"
                f"Open this link to choose a new password:\n{reset_url}\n\n"
                "If you did not request this, you can ignore this email."
            ),
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
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
