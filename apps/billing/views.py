import hashlib
import json
import logging

from django.db import transaction
from django.http import Http404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.quotas.models import StorageQuota

from .models import BillingPlan, PaymentTransaction, Subscription, WebhookEvent
from .paystack import PaystackAPIError, PaystackConfigurationError, PaystackClient, verify_webhook_signature
from .serializers import (
    BillingPlanSerializer,
    CheckoutSerializer,
    PaymentTransactionSerializer,
    SubscriptionSerializer,
    VerifyPaymentSerializer,
)
from .services import create_checkout, verify_and_fulfill
from .tasks import disable_replaced_subscriptions, process_paystack_webhook

logger = logging.getLogger(__name__)


def _processor_error(exc):
    if isinstance(exc, PaystackConfigurationError):
        return Response({"detail": str(exc), "code": "paystack_not_configured"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    if isinstance(exc, PaystackAPIError):
        return Response({"detail": str(exc), "code": "paystack_error"}, status=status.HTTP_502_BAD_GATEWAY)
    return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PlanListView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        plans = BillingPlan.objects.filter(is_active=True)
        return Response(BillingPlanSerializer(plans, many=True).data)


class BillingSummaryView(views.APIView):
    def get(self, request):
        active_statuses = [Subscription.STATUS_ACTIVE, Subscription.STATUS_PAST_DUE, Subscription.STATUS_NON_RENEWING]
        subscription = (
            Subscription.objects.filter(user=request.user, status__in=active_statuses)
            .select_related("plan")
            .order_by("-created_at")
            .first()
        )
        quota = StorageQuota.objects.get_or_create(user=request.user)[0]
        current_plan = subscription.plan if subscription else BillingPlan.objects.get(slug=quota.plan_name if quota.plan_name else "free")
        transactions = PaymentTransaction.objects.filter(user=request.user).select_related("plan")[:20]
        return Response(
            {
                "current_plan": BillingPlanSerializer(current_plan).data,
                "subscription": SubscriptionSerializer(subscription).data if subscription else None,
                "quota": {
                    "storage_used_bytes": quota.storage_used_bytes,
                    "storage_limit_bytes": quota.storage_limit_bytes,
                    "storage_remaining_bytes": max(0, quota.storage_limit_bytes - quota.storage_used_bytes),
                },
                "transactions": PaymentTransactionSerializer(transactions, many=True).data,
            }
        )


class CheckoutView(views.APIView):
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment, checkout = create_checkout(request.user, serializer.validated_data["plan"])
        except (PaystackConfigurationError, PaystackAPIError, ValueError) as exc:
            return _processor_error(exc)
        return Response(
            {
                "authorization_url": checkout["authorization_url"],
                "access_code": checkout["access_code"],
                "reference": payment.reference,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyPaymentView(views.APIView):
    def post(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment, subscription, replaced_ids = verify_and_fulfill(serializer.validated_data["reference"], request.user)
        except PaymentTransaction.DoesNotExist:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)
        except (PaystackConfigurationError, PaystackAPIError, ValueError) as exc:
            return _processor_error(exc)
        if replaced_ids:
            disable_replaced_subscriptions.delay(replaced_ids)
        return Response(
            {
                "detail": "Payment verified and plan activated.",
                "transaction": PaymentTransactionSerializer(payment).data,
                "subscription": SubscriptionSerializer(subscription).data,
            }
        )


def _current_subscription(user, include_cancelled=False):
    statuses = [Subscription.STATUS_ACTIVE, Subscription.STATUS_PAST_DUE, Subscription.STATUS_NON_RENEWING]
    if include_cancelled:
        statuses.append(Subscription.STATUS_CANCELLED)
    subscription = (
        Subscription.objects.select_related("plan")
        .filter(user=user, status__in=statuses)
        .order_by("-created_at")
        .first()
    )
    if subscription is None:
        raise Http404("No subscription found.")
    return subscription


class CancelSubscriptionView(views.APIView):
    def post(self, request):
        subscription = _current_subscription(request.user)
        if not subscription.paystack_subscription_code or not subscription.paystack_email_token:
            return Response(
                {"detail": "Paystack is still finalizing this subscription. Try again in a moment."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            PaystackClient().disable_subscription(subscription.paystack_subscription_code, subscription.paystack_email_token)
        except (PaystackConfigurationError, PaystackAPIError) as exc:
            return _processor_error(exc)
        subscription.status = Subscription.STATUS_NON_RENEWING
        subscription.cancel_at_period_end = True
        subscription.save(update_fields=["status", "cancel_at_period_end", "updated_at"])
        return Response({"detail": "Your subscription will not renew.", "subscription": SubscriptionSerializer(subscription).data})


class ResumeSubscriptionView(views.APIView):
    def post(self, request):
        subscription = _current_subscription(request.user, include_cancelled=True)
        if not subscription.paystack_subscription_code or not subscription.paystack_email_token:
            return Response({"detail": "This subscription cannot be resumed yet."}, status=status.HTTP_409_CONFLICT)
        try:
            PaystackClient().enable_subscription(subscription.paystack_subscription_code, subscription.paystack_email_token)
        except (PaystackConfigurationError, PaystackAPIError) as exc:
            return _processor_error(exc)
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.cancel_at_period_end = False
        subscription.cancelled_at = None
        subscription.save(update_fields=["status", "cancel_at_period_end", "cancelled_at", "updated_at"])
        return Response({"detail": "Your subscription is active again.", "subscription": SubscriptionSerializer(subscription).data})


class PaymentMethodView(views.APIView):
    def post(self, request):
        subscription = _current_subscription(request.user)
        if not subscription.paystack_subscription_code:
            return Response({"detail": "Paystack is still finalizing this subscription."}, status=status.HTTP_409_CONFLICT)
        try:
            result = PaystackClient().management_link(subscription.paystack_subscription_code)
        except (PaystackConfigurationError, PaystackAPIError) as exc:
            return _processor_error(exc)
        return Response({"link": result.get("link")})


class PaystackWebhookView(views.APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        raw_body = request.body
        if not verify_webhook_signature(
            raw_body,
            request.headers.get("Paystack-Signature", ""),
            request.headers.get("X-Paystack-Signature", ""),
        ):
            return Response({"detail": "Invalid webhook signature."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return Response({"detail": "Invalid JSON."}, status=status.HTTP_400_BAD_REQUEST)

        data = payload.get("data") or {}
        resource_id = str(data.get("id") or data.get("reference") or data.get("subscription_code") or "")
        fingerprint = hashlib.sha256(raw_body).hexdigest()
        event, created = WebhookEvent.objects.get_or_create(
            fingerprint=fingerprint,
            defaults={
                "event_type": payload.get("event", "unknown"),
                "provider_resource_id": resource_id,
                "payload": payload,
            },
        )
        if created:
            try:
                process_paystack_webhook.delay(str(event.id))
            except Exception:
                logger.exception("Paystack event %s was saved but could not be queued.", event.id)
        return Response({"received": True})
