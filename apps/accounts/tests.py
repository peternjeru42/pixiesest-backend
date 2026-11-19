from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from google.auth import exceptions as google_auth_exceptions
from rest_framework import status
from rest_framework.test import APIClient

from .models import SignupVerificationCode, User
from .serializers import EmailDeliveryError, send_signup_verification_code


class SignupEmailDeliveryTests(TestCase):
    def test_signup_email_timeout_removes_unsent_code(self):
        with patch("apps.accounts.serializers.send_mail", side_effect=TimeoutError("timed out")):
            with self.assertRaises(EmailDeliveryError):
                send_signup_verification_code("User@Example.com")

        self.assertFalse(SignupVerificationCode.objects.filter(email__iexact="user@example.com").exists())

    def test_register_returns_service_unavailable_when_signup_email_fails(self):
        client = APIClient()
        payload = {
            "email": "user@example.com",
            "password": "strong-password",
            "first_name": "Test",
            "last_name": "User",
            "business_name": "Studio",
            "phone_number": "",
        }

        with patch("apps.accounts.serializers.send_mail", side_effect=TimeoutError("timed out")):
            response = client.post(reverse("auth-register"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("Signup verification email could not be sent", response.data["detail"])
        self.assertFalse(SignupVerificationCode.objects.filter(email__iexact=payload["email"]).exists())

    @override_settings(GOOGLE_CLIENT_ID="google-client-id")
    def test_google_auth_returns_service_unavailable_when_google_verification_fails(self):
        client = APIClient()

        with patch(
            "apps.accounts.views.id_token.verify_oauth2_token",
            side_effect=google_auth_exceptions.TransportError("failed"),
        ):
            response = client.post(
                reverse("auth-google"),
                {"credential": "credential", "intent": "login"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data["detail"], "Google authentication is temporarily unavailable. Please try again.")

    @override_settings(GOOGLE_CLIENT_ID="google-client-id")
    def test_google_signup_logs_in_an_existing_google_account(self):
        user = User.objects.create_user(
            email="existing@example.com",
            google_sub="google-user-123",
            password=None,
        )
        google_profile = {
            "iss": "https://accounts.google.com",
            "sub": "google-user-123",
            "email": user.email,
            "email_verified": True,
        }

        with patch("apps.accounts.views.id_token.verify_oauth2_token", return_value=google_profile):
            response = APIClient().post(
                reverse("auth-google"),
                {"credential": "credential", "intent": "signup"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], str(user.id))
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    @override_settings(GOOGLE_CLIENT_ID="google-client-id")
    def test_google_signup_links_and_logs_in_an_existing_email_account(self):
        user = User.objects.create_user(
            email="existing@example.com",
            password="strong-password",
        )
        google_profile = {
            "iss": "https://accounts.google.com",
            "sub": "google-user-456",
            "email": user.email,
            "email_verified": True,
        }

        with patch("apps.accounts.views.id_token.verify_oauth2_token", return_value=google_profile):
            response = APIClient().post(
                reverse("auth-google"),
                {"credential": "credential", "intent": "signup"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], str(user.id))
        user.refresh_from_db()
        self.assertEqual(user.google_sub, "google-user-456")
