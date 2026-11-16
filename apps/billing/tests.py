import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.quotas.models import StorageQuota

from .models import BillingPlan, PaymentTransaction, Subscription, WebhookEvent
from .paystack import verify_webhook_signature


@override_settings(PAYSTACK_WEBHOOK_SECRET="whsec_test", PAYSTACK_SECRET_KEY="sk_test_123")
class WebhookSignatureTests(SimpleTestCase):
    def test_timestamped_signature_is_verified(self):
        body = b'{"event":"ping","data":{}}'
        timestamp = int(time.time())
        signature = hmac.new(
            b"whsec_test",
            str(timestamp).encode() + b"." + body,
            hashlib.sha512,
        ).hexdigest()

        self.assertTrue(verify_webhook_signature(body, f"t={timestamp},v1=whk_test:{signature}", ""))

    def test_old_timestamp_is_rejected(self):
        body = b"{}"
        timestamp = int(time.time()) - 301
        signature = hmac.new(
            b"whsec_test",
            str(timestamp).encode() + b"." + body,
            hashlib.sha512,
        ).hexdigest()

        self.assertFalse(verify_webhook_signature(body, f"t={timestamp},v1=whk_test:{signature}", ""))

    def test_legacy_signature_remains_supported(self):
        body = b'{"event":"ping"}'
        signature = hmac.new(b"sk_test_123", body, hashlib.sha512).hexdigest()
        self.assertTrue(verify_webhook_signature(body, "", signature))


@override_settings(
    PAYSTACK_SECRET_KEY="sk_test_123",
    PAYSTACK_WEBHOOK_SECRET="whsec_test",
    FRONTEND_URL="https://droptop.example",
    CELERY_TASK_ALWAYS_EAGER=True,
)
class BillingAPITests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="owner@example.com", password="password123")
        self.client.force_authenticate(self.user)
        self.basic = BillingPlan.objects.get(slug="basic")

    def test_plan_catalog_has_the_four_droptop_plans(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse("billing-plans"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([plan["slug"] for plan in response.data], ["free", "basic", "plus", "pro"])
        self.assertEqual([plan["amount_minor"] for plan in response.data], [0, 500, 1200, 2000])

    @patch("apps.billing.services.PaystackClient.initialize_transaction")
    @patch("apps.billing.services.PaystackClient.create_plan")
    def test_checkout_creates_provider_plan_and_server_transaction(self, create_plan, initialize):
        create_plan.return_value = {"plan_code": "PLN_basic"}
        initialize.return_value = {
            "authorization_url": "https://checkout.paystack.com/abc",
            "access_code": "abc",
            "reference": "ignored",
        }

        response = self.client.post(reverse("billing-checkout"), {"plan": "basic"}, format="json")

        self.assertEqual(response.status_code, 201)
        payment = PaymentTransaction.objects.get(reference=response.data["reference"])
        self.assertEqual(payment.expected_amount_minor, 500)
        self.assertEqual(payment.currency, "USD")
        self.basic.refresh_from_db()
        self.assertEqual(self.basic.paystack_test_plan_code, "PLN_basic")
        initialize.assert_called_once()
        self.assertEqual(initialize.call_args.kwargs["plan_code"], "PLN_basic")

    @patch("apps.billing.services.PaystackClient.verify_transaction")
    def test_verify_activates_plan_and_updates_storage_quota(self, verify):
        payment = PaymentTransaction.objects.create(
            user=self.user,
            plan=self.basic,
            reference="dtp-test-reference",
            expected_amount_minor=500,
            currency="USD",
        )
        verify.return_value = {
            "id": 12345,
            "status": "success",
            "reference": payment.reference,
            "amount": 500,
            "currency": "USD",
            "channel": "card",
            "customer": {"customer_code": "CUS_123", "email": self.user.email},
            "authorization": {"brand": "visa", "last4": "4081"},
        }

        response = self.client.post(reverse("billing-verify"), {"reference": payment.reference}, format="json")

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentTransaction.STATUS_SUCCESS)
        self.assertEqual(payment.provider_payload["card"]["last4"], "4081")
        subscription = Subscription.objects.get(user=self.user)
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)
        quota = StorageQuota.objects.get(user=self.user)
        self.assertEqual(quota.plan_name, "basic")
        self.assertEqual(quota.storage_limit_bytes, 10 * 1024**3)

    @patch("apps.billing.views.process_paystack_webhook.delay")
    def test_duplicate_webhook_is_saved_and_queued_once(self, delay):
        self.client.force_authenticate(user=None)
        body = json.dumps({"event": "ping", "data": {"id": 77}}, separators=(",", ":")).encode()
        signature = hmac.new(b"sk_test_123", body, hashlib.sha512).hexdigest()
        url = reverse("paystack-webhook")

        first = self.client.generic("POST", url, body, content_type="application/json", HTTP_X_PAYSTACK_SIGNATURE=signature)
        second = self.client.generic("POST", url, body, content_type="application/json", HTTP_X_PAYSTACK_SIGNATURE=signature)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(WebhookEvent.objects.count(), 1)
        delay.assert_called_once()

    def test_webhook_rejects_an_invalid_signature(self):
        self.client.force_authenticate(user=None)
        response = self.client.generic(
            "POST",
            reverse("paystack-webhook"),
            b'{}',
            content_type="application/json",
            HTTP_X_PAYSTACK_SIGNATURE="invalid",
        )
        self.assertEqual(response.status_code, 401)

    def test_summary_starts_on_free_plan(self):
        response = self.client.get(reverse("billing-summary"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["current_plan"]["slug"], "free")
        self.assertEqual(response.data["quota"]["storage_limit_bytes"], 5 * 1024**3)
