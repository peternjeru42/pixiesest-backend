import logging

from django.db import transaction
from django.utils import timezone

from .models import PaymentTransaction, Subscription, WebhookEvent
from .services import (
    apply_plan_entitlements,
    find_plan_from_paystack_data,
    find_subscription_from_paystack_data,
    fulfill_verified_payment,
    mark_subscription_cancelled,
    mark_subscription_past_due,
    sync_subscription_created,
)

logger = logging.getLogger(__name__)


def _reference(data):
    return data.get("reference") or data.get("transaction", {}).get("reference")


def _process_charge_success(data):
    reference = _reference(data)
    payment = PaymentTransaction.objects.filter(reference=reference).select_related("plan", "user").first()
    if payment:
        subscription, replaced_ids = fulfill_verified_payment(payment, data)
        return {"subscription_id": str(subscription.id), "replaced_ids": replaced_ids}

    subscription = find_subscription_from_paystack_data(data)
    plan = find_plan_from_paystack_data(data) or (subscription.plan if subscription else None)
    if not subscription or not plan or not reference:
        return {}
    payment, created = PaymentTransaction.objects.get_or_create(
        reference=reference,
        defaults={
            "user": subscription.user,
            "plan": plan,
            "subscription": subscription,
            "provider_mode": subscription.provider_mode,
            "provider_transaction_id": data.get("id"),
            "expected_amount_minor": int(data.get("amount") or plan.amount_minor),
            "currency": data.get("currency") or plan.currency,
            "status": PaymentTransaction.STATUS_SUCCESS,
            "channel": data.get("channel") or "",
            "paid_at": timezone.now(),
        },
    )
    if created:
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.grace_period_ends_at = None
        subscription.next_payment_at = None
        subscription.save(update_fields=["status", "grace_period_ends_at", "next_payment_at", "updated_at"])
        apply_plan_entitlements(subscription.user, plan)
        from apps.notifications.tasks import send_payment_success_email

        transaction.on_commit(lambda: send_payment_success_email.delay(str(payment.id)), robust=True)
    return {"subscription_id": str(subscription.id)}


def _process_invoice_update(data):
    subscription = find_subscription_from_paystack_data(data)
    if not subscription:
        return {}
    if data.get("paid") is True or data.get("status") in {"success", "paid"}:
        subscription.status = Subscription.STATUS_ACTIVE
        subscription.grace_period_ends_at = None
        subscription.save(update_fields=["status", "grace_period_ends_at", "updated_at"])
        apply_plan_entitlements(subscription.user, subscription.plan)
    return {"subscription_id": str(subscription.id)}


def process_event(event):
    event_type = event.event_type
    data = event.payload.get("data") or {}
    result = {}
    if event_type == "charge.success":
        result = _process_charge_success(data)
    elif event_type == "subscription.create":
        subscription = sync_subscription_created(data)
        result = {"subscription_id": str(subscription.id)} if subscription else {}
    elif event_type == "invoice.update":
        result = _process_invoice_update(data)
    elif event_type == "invoice.payment_failed":
        subscription = find_subscription_from_paystack_data(data)
        if subscription:
            mark_subscription_past_due(subscription)
            from apps.notifications.tasks import send_payment_failed_email

            transaction.on_commit(
                lambda: send_payment_failed_email.delay(str(subscription.id), str(event.id)),
                robust=True,
            )
            result = {"subscription_id": str(subscription.id)}
    elif event_type == "subscription.not_renew":
        subscription = find_subscription_from_paystack_data(data)
        if subscription:
            subscription.status = Subscription.STATUS_NON_RENEWING
            subscription.cancel_at_period_end = True
            subscription.save(update_fields=["status", "cancel_at_period_end", "updated_at"])
            result = {"subscription_id": str(subscription.id)}
    elif event_type == "subscription.disable":
        subscription = find_subscription_from_paystack_data(data)
        if subscription:
            mark_subscription_cancelled(subscription)
            result = {"subscription_id": str(subscription.id)}
    return result


def process_webhook_event(event_id):
    with transaction.atomic():
        event = WebhookEvent.objects.select_for_update().get(pk=event_id)
        if event.status == WebhookEvent.STATUS_PROCESSED:
            return
        event.status = WebhookEvent.STATUS_PROCESSING
        event.attempts += 1
        event.last_error = ""
        event.save(update_fields=["status", "attempts", "last_error", "updated_at"])

    try:
        process_event(event)
    except Exception as exc:
        logger.exception("Unable to process Paystack webhook event %s", event_id)
        WebhookEvent.objects.filter(pk=event_id).update(
            status=WebhookEvent.STATUS_FAILED,
            last_error=str(exc)[:4000],
        )
        raise
    else:
        WebhookEvent.objects.filter(pk=event_id).update(
            status=WebhookEvent.STATUS_PROCESSED,
            processed_at=timezone.now(),
            last_error="",
        )
