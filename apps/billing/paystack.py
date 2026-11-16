import hashlib
import hmac
import json
import time

import requests
from django.conf import settings


class PaystackConfigurationError(RuntimeError):
    pass


class PaystackAPIError(RuntimeError):
    def __init__(self, message, status_code=502):
        super().__init__(message)
        self.status_code = status_code


def provider_mode():
    return "live" if settings.PAYSTACK_SECRET_KEY.startswith("sk_live_") else "test"


class PaystackClient:
    def __init__(self):
        if not settings.PAYSTACK_SECRET_KEY:
            raise PaystackConfigurationError("Paystack is not configured on the server.")
        self.base_url = settings.PAYSTACK_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def _request(self, method, path, *, payload=None):
        try:
            response = requests.request(
                method,
                f"{self.base_url}{path}",
                headers=self.headers,
                json=payload,
                timeout=settings.PAYSTACK_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise PaystackAPIError("Paystack could not be reached. Please try again.") from exc

        body = response.json() if response.content else {}
        if not response.ok or not body.get("status"):
            message = body.get("message") or "Paystack rejected the request."
            raise PaystackAPIError(message, response.status_code)
        return body.get("data")

    def create_plan(self, plan):
        return self._request(
            "POST",
            "/plan",
            payload={
                "name": f"Droptop {plan.name} Monthly",
                "description": f"{plan.name} plan with {plan.storage_limit_bytes // 1024**3:,} GB storage",
                "amount": plan.amount_minor,
                "interval": plan.interval,
                "currency": plan.currency,
                "send_invoices": True,
                "send_sms": False,
            },
        )

    def fetch_plan(self, plan_code):
        return self._request("GET", f"/plan/{plan_code}")

    def initialize_transaction(self, *, email, amount, currency, plan_code, reference, callback_url, metadata):
        return self._request(
            "POST",
            "/transaction/initialize",
            payload={
                "email": email,
                "amount": str(amount),
                "currency": currency,
                "plan": plan_code,
                "reference": reference,
                "callback_url": callback_url,
                "channels": ["card"],
                "metadata": json.dumps(metadata),
            },
        )

    def verify_transaction(self, reference):
        return self._request("GET", f"/transaction/verify/{reference}")

    def disable_subscription(self, code, token):
        return self._request("POST", "/subscription/disable", payload={"code": code, "token": token})

    def enable_subscription(self, code, token):
        return self._request("POST", "/subscription/enable", payload={"code": code, "token": token})

    def management_link(self, code):
        return self._request("GET", f"/subscription/{code}/manage/link")


def verify_webhook_signature(raw_body, timestamped_signature, legacy_signature):
    webhook_secret = settings.PAYSTACK_WEBHOOK_SECRET
    if timestamped_signature and webhook_secret:
        values = {}
        signatures = []
        for part in timestamped_signature.split(","):
            key, separator, value = part.strip().partition("=")
            if not separator:
                continue
            if key == "v1":
                signatures.append(value.split(":", 1)[-1])
            else:
                values[key] = value
        try:
            timestamp = int(values.get("t", "0"))
        except ValueError:
            return False
        if abs(int(time.time()) - timestamp) > 300:
            return False
        signed_payload = str(timestamp).encode() + b"." + raw_body
        expected = hmac.new(webhook_secret.encode(), signed_payload, hashlib.sha512).hexdigest()
        return any(hmac.compare_digest(expected, signature) for signature in signatures)

    secret_key = settings.PAYSTACK_SECRET_KEY
    if legacy_signature and secret_key:
        expected = hmac.new(secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, legacy_signature)
    return False
