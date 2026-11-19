import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.quotas.models import StorageQuota

from .models import BillingCustomer, BillingPlan, PaymentTransaction, Subscription
from .paystack import PaystackAPIError, PaystackClient, provider_mode

logger = logging.getLogger(__name__)


def _parse_date(value):
    if not value:
        return None
    parsed = parse_datetime(value) if isinstance(value, str) else value
    return parsed


def _plan_code_field():
    return "paystack_live_plan_code" if provider_mode() == "live" else "paystack_test_plan_code"


def _safe_payment_payload(data):
    customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}
    authorization = data.get("authorization") if isinstance(data.get("authorization"), dict) else {}
    return {
        "status": data.get("status"),
        "reference": data.get("reference"),
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "channel": data.get("channel"),
        "paid_at": data.get("paid_at") or data.get("paidAt"),
        "customer_code": customer.get("customer_code"),
        "card": {
            "brand": authorization.get("brand"),
            "last4": authorization.get("last4"),
            "exp_month": authorization.get("exp_month"),
            "exp_year": authorization.get("exp_year"),
        },
    }


def ensure_paystack_plan(plan):
    if plan.amount_minor == 0:
        raise ValueError("The free plan does not require a Paystack plan.")
    field = _plan_code_field()
    code = getattr(plan, field)
    client = PaystackClient()
    if code:
        try:
            remote = client.fetch_plan(code)
            if (
                int(remote.get("amount", -1)) == plan.amount_minor
                and remote.get("currency") == plan.currency
                and remote.get("interval") == plan.interval
            ):
                return code
        except PaystackAPIError:
            logger.warning("Stored Paystack plan %s could not be fetched; creating a replacement.", code)

    with transaction.atomic():
        locked = BillingPlan.objects.select_for_update().get(pk=plan.pk)
        current = getattr(locked, field)
        if current and current != code:
            return current
        remote = client.create_plan(locked)
        setattr(locked, field, remote["plan_code"])
        locked.save(update_fields=[field, "updated_at"])
        return remote["plan_code"]


def create_checkout(user, plan):
    if plan.amount_minor == 0 or not plan.is_active:
        raise ValueError("Choose an active paid plan.")
    plan_code = ensure_paystack_plan(plan)
    reference = f"dtp-{uuid.uuid4().hex}"
    payment = PaymentTransaction.objects.create(
        user=user,
        plan=plan,
        reference=reference,
        provider_mode=provider_mode(),
        expected_amount_minor=plan.amount_minor,
        currency=plan.currency,
    )
    callback_url = f"{settings.FRONTEND_URL.rstrip('/')}/billing/callback"
    metadata = {
        "droptop_user_id": str(user.id),
        "droptop_plan": plan.slug,
        "droptop_transaction_id": str(payment.id),
        "cancel_action": f"{settings.FRONTEND_URL.rstrip('/')}/dashboard/billing?checkout=cancelled",
    }
    try:
        checkout = PaystackClient().initialize_transaction(
            email=user.email,
            amount=plan.amount_minor,
            currency=plan.currency,
            plan_code=plan_code,
            reference=reference,
            callback_url=callback_url,
            metadata=metadata,
        )
    except Exception:
        payment.status = PaymentTransaction.STATUS_FAILED
        payment.save(update_fields=["status", "updated_at"])
        raise
    return payment, checkout


def _customer_details(data):
    customer = data.get("customer")
    if isinstance(customer, dict):
        return customer.get("customer_code", ""), customer.get("email", "")
    return "", ""


@transaction.atomic
def fulfill_verified_payment(payment, data):
    payment = PaymentTransaction.objects.select_for_update().select_related("plan", "user").get(pk=payment.pk)
    if payment.status == PaymentTransaction.STATUS_SUCCESS and payment.subscription_id:
        return payment.subscription, []

    if data.get("status") != "success":
        raise ValueError("The Paystack transaction is not successful.")
    if int(data.get("amount", -1)) != payment.expected_amount_minor:
        raise ValueError("The payment amount does not match the selected plan.")
    if str(data.get("currency", "")).upper() != payment.currency.upper():
        raise ValueError("The payment currency does not match the selected plan.")
    if data.get("reference") != payment.reference:
        raise ValueError("The payment reference does not match.")

    customer_code, customer_email = _customer_details(data)
    BillingCustomer.objects.update_or_create(
        user=payment.user,
        defaults={
            "email": customer_email or payment.user.email,
            "paystack_customer_code": customer_code,
        },
    )

    replaced = list(
        Subscription.objects.select_for_update()
        .filter(
            user=payment.user,
            status__in=[Subscription.STATUS_ACTIVE, Subscription.STATUS_PAST_DUE, Subscription.STATUS_NON_RENEWING],
        )
        .exclude(pk=payment.subscription_id)
    )
    subscription = payment.subscription
    if subscription is None:
        subscription = Subscription.objects.create(
            user=payment.user,
            plan=payment.plan,
            status=Subscription.STATUS_ACTIVE,
            provider_mode=payment.provider_mode,
            paystack_customer_code=customer_code,
        )
    else:
        subscription.plan = payment.plan
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.cancel_at_period_end = False
        subscription.grace_period_ends_at = None
        if customer_code:
            subscription.paystack_customer_code = customer_code
        subscription.save()

    replaced_ids = []
    for old in replaced:
        if old.pk == subscription.pk:
            continue
        old.status = Subscription.STATUS_NON_RENEWING
        old.cancel_at_period_end = True
        old.save(update_fields=["status", "cancel_at_period_end", "updated_at"])
        replaced_ids.append(str(old.id))

    payment.subscription = subscription
    payment.status = PaymentTransaction.STATUS_SUCCESS
    payment.provider_transaction_id = data.get("id")
    payment.channel = data.get("channel") or ""
    payment.paid_at = _parse_date(data.get("paid_at") or data.get("paidAt")) or timezone.now()
    payment.provider_payload = _safe_payment_payload(data)
    payment.save()
    apply_plan_entitlements(payment.user, payment.plan)
    from apps.notifications.tasks import send_payment_success_email

    transaction.on_commit(lambda: send_payment_success_email.delay(str(payment.id)), robust=True)
    return subscription, replaced_ids


def verify_and_fulfill(reference, user=None):
    query = PaymentTransaction.objects.select_related("plan", "user")
    if user is not None:
        query = query.filter(user=user)
    payment = query.get(reference=reference)
    data = PaystackClient().verify_transaction(reference)
    subscription, replaced_ids = fulfill_verified_payment(payment, data)
    payment.refresh_from_db()
    return payment, subscription, replaced_ids


def apply_plan_entitlements(user, plan):
    StorageQuota.objects.update_or_create(
        user=user,
        defaults={
            "plan_name": plan.slug,
            "storage_limit_bytes": plan.storage_limit_bytes,
            "is_active": True,
        },
    )


def downgrade_to_free(user):
    free = BillingPlan.objects.get(slug="free")
    apply_plan_entitlements(user, free)


def find_plan_from_paystack_data(data):
    plan_data = data.get("plan") or {}
    code = plan_data.get("plan_code") if isinstance(plan_data, dict) else plan_data
    if not code:
        return None
    return BillingPlan.objects.filter(
        **{_plan_code_field(): code},
    ).first()


def find_subscription_from_paystack_data(data):
    code = data.get("subscription_code")
    if not code and isinstance(data.get("subscription"), dict):
        code = data["subscription"].get("subscription_code")
    if code:
        found = Subscription.objects.filter(paystack_subscription_code=code).select_related("user", "plan").first()
        if found:
            return found

    customer = data.get("customer") or {}
    customer_code = customer.get("customer_code") if isinstance(customer, dict) else ""
    plan = find_plan_from_paystack_data(data)
    query = Subscription.objects.select_related("user", "plan")
    if customer_code:
        query = query.filter(paystack_customer_code=customer_code)
    if plan:
        query = query.filter(plan=plan)
    return query.order_by("-created_at").first()


@transaction.atomic
def sync_subscription_created(data):
    plan = find_plan_from_paystack_data(data)
    if not plan:
        return None
    customer = data.get("customer") or {}
    customer_code = customer.get("customer_code", "") if isinstance(customer, dict) else ""
    email = customer.get("email", "") if isinstance(customer, dict) else ""
    user = None
    if customer_code:
        billing_customer = BillingCustomer.objects.filter(paystack_customer_code=customer_code).select_related("user").first()
        user = billing_customer.user if billing_customer else None
    if user is None and email:
        user = get_user_model().objects.filter(email__iexact=email).first()
    if user is None:
        return None

    code = data.get("subscription_code")
    subscription = (
        Subscription.objects.select_for_update().filter(paystack_subscription_code=code).first()
        if code
        else None
    )
    if subscription is None:
        subscription = (
            Subscription.objects.select_for_update()
            .filter(user=user, plan=plan, paystack_subscription_code__isnull=True)
            .order_by("-created_at")
            .first()
        )
    if subscription is None:
        subscription = Subscription(user=user, plan=plan, provider_mode=provider_mode())
    subscription.status = Subscription.STATUS_ACTIVE
    subscription.paystack_subscription_code = code or subscription.paystack_subscription_code
    subscription.paystack_email_token = data.get("email_token") or subscription.paystack_email_token
    subscription.paystack_customer_code = customer_code or subscription.paystack_customer_code
    subscription.next_payment_at = _parse_date(data.get("next_payment_date"))
    subscription.cancel_at_period_end = False
    subscription.grace_period_ends_at = None
    subscription.save()
    apply_plan_entitlements(user, plan)
    return subscription


@transaction.atomic
def mark_subscription_past_due(subscription):
    subscription = Subscription.objects.select_for_update().get(pk=subscription.pk)
    subscription.status = Subscription.STATUS_PAST_DUE
    subscription.grace_period_ends_at = timezone.now() + timedelta(days=settings.BILLING_GRACE_PERIOD_DAYS)
    subscription.save(update_fields=["status", "grace_period_ends_at", "updated_at"])
    return subscription


@transaction.atomic
def mark_subscription_cancelled(subscription):
    subscription = Subscription.objects.select_for_update().select_related("user").get(pk=subscription.pk)
    if subscription.cancel_at_period_end and subscription.next_payment_at and subscription.next_payment_at > timezone.now():
        subscription.status = Subscription.STATUS_NON_RENEWING
        subscription.cancelled_at = timezone.now()
        subscription.save(update_fields=["status", "cancelled_at", "updated_at"])
        return subscription
    subscription.status = Subscription.STATUS_CANCELLED
    subscription.cancelled_at = timezone.now()
    subscription.cancel_at_period_end = False
    subscription.save(update_fields=["status", "cancelled_at", "cancel_at_period_end", "updated_at"])
    has_other = Subscription.objects.filter(
        user=subscription.user,
        status__in=[Subscription.STATUS_ACTIVE, Subscription.STATUS_PAST_DUE, Subscription.STATUS_NON_RENEWING],
    ).exclude(pk=subscription.pk).exists()
    if not has_other:
        downgrade_to_free(subscription.user)
    return subscription
