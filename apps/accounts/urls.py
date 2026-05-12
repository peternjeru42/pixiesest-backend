from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    EmailResendVerificationView,
    EmailVerifyView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("email/verify/", EmailVerifyView.as_view(), name="email-verify"),
    path("email/resend-verification/", EmailResendVerificationView.as_view(), name="email-resend-verification"),
    path("me/", MeView.as_view(), name="auth-me"),
]
