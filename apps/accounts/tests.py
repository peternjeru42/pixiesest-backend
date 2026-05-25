from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from google.auth import exceptions as google_auth_exceptions
from rest_framework import status
from rest_framework.test import APIClient

from .models import SignupVerificationCode
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
