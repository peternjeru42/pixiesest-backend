from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import generics, permissions, status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import (
    EmailTokenSerializer,
    GoogleAuthSerializer,
    LoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {"user": UserSerializer(user).data, "refresh": str(refresh), "access": str(refresh.access_token)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class GoogleAuthView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not settings.GOOGLE_CLIENT_ID:
            raise ValidationError("Google authentication is not configured.")

        try:
            google_profile = id_token.verify_oauth2_token(
                serializer.validated_data["credential"],
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError as exc:
            raise AuthenticationFailed("Invalid Google credential.") from exc

        if google_profile.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
            raise AuthenticationFailed("Invalid Google issuer.")
        if not google_profile.get("email_verified"):
            raise AuthenticationFailed("Google email is not verified.")

        google_sub = google_profile.get("sub")
        email = google_profile.get("email", "").strip().lower()
        intent = serializer.validated_data["intent"]
        if not google_sub or not email:
            raise AuthenticationFailed("Google credential is missing required account details.")

        with transaction.atomic():
            user = User.objects.filter(google_sub=google_sub).first()
            if user is None:
                user = User.objects.filter(email__iexact=email).first()

            if user is None:
                user = User.objects.create_user(
                    email=email,
                    password=None,
                    google_sub=google_sub,
                    first_name=google_profile.get("given_name", ""),
                    last_name=google_profile.get("family_name", ""),
                    profile_photo_url=google_profile.get("picture", ""),
                    last_login=timezone.now(),
                )
            else:
                if user.google_sub and user.google_sub != google_sub:
                    raise AuthenticationFailed("This email is already linked to another Google account.")
                if not user.is_active:
                    raise AuthenticationFailed("User account is disabled.")
                if intent == "signup" and user.google_sub == google_sub:
                    return Response(
                        {
                            "code": "google_account_exists",
                            "detail": "This Google account already exists. Please sign in with Google.",
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                update_fields = ["last_login"]
                user.last_login = timezone.now()

                if not user.google_sub:
                    user.google_sub = google_sub
                    update_fields.append("google_sub")

                profile_updates = {
                    "first_name": google_profile.get("given_name", ""),
                    "last_name": google_profile.get("family_name", ""),
                    "profile_photo_url": google_profile.get("picture", ""),
                }
                for field, value in profile_updates.items():
                    if value and not getattr(user, field):
                        setattr(user, field, value)
                        update_fields.append(field)

                user.save(update_fields=update_fields)

        refresh = RefreshToken.for_user(user)
        return Response(
            {"user": UserSerializer(user).data, "refresh": str(refresh), "access": str(refresh.access_token)}
        )


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RefreshToken(serializer.validated_data["refresh"]).blacklist()
        except TokenError:
            # Logout should be idempotent for expired or already-blacklisted refresh tokens.
            pass

        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "If the email exists, reset instructions will be sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "Password reset token accepted by placeholder implementation."})


class EmailVerifyView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = EmailTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "Email verification accepted by placeholder implementation."})


class EmailResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "auth"

    def post(self, request):
        serializer = EmailTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": "If the email exists, verification instructions will be sent."})
