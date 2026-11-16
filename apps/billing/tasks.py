import logging

from celery import shared_task
from django.utils import timezone

from .models import Subscription, WebhookEvent
from .paystack import PaystackClient
from .services import downgrade_to_free, mark_subscription_cancelled
from .webhooks import process_webhook_event

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True, max_retries=5)
def process_paystack_webhook(self, event_id):
    process_webhook_event(event_id)


@shared_task
def process_pending_webhooks():
    event_ids = list(
        WebhookEvent.objects.filter(status__in=[WebhookEvent.STATUS_PENDING, WebhookEvent.STATUS_FAILED], attempts__lt=6)
        .order_by("created_at")
        .values_list("id", flat=True)[:100]
    )
    for event_id in event_ids:
        process_paystack_webhook.delay(str(event_id))
    return len(event_ids)


@shared_task
def disable_replaced_subscriptions(subscription_ids):
    client = PaystackClient()
    disabled = 0
    for subscription in Subscription.objects.filter(id__in=subscription_ids):
        if not subscription.paystack_subscription_code or not subscription.paystack_email_token:
            continue
        try:
            client.disable_subscription(subscription.paystack_subscription_code, subscription.paystack_email_token)
            disabled += 1
        except Exception:
            logger.exception("Unable to disable replaced subscription %s", subscription.id)
    return disabled


@shared_task
def expire_billing_grace_periods():
    past_due_subscriptions = Subscription.objects.filter(
        status=Subscription.STATUS_PAST_DUE,
        grace_period_ends_at__lte=timezone.now(),
    ).select_related("user")
    expired = 0
    for subscription in past_due_subscriptions:
        subscription.status = Subscription.STATUS_EXPIRED
        subscription.save(update_fields=["status", "updated_at"])
        has_other = Subscription.objects.filter(user=subscription.user, status=Subscription.STATUS_ACTIVE).exclude(pk=subscription.pk).exists()
        if not has_other:
            downgrade_to_free(subscription.user)
        expired += 1

    ended_subscriptions = Subscription.objects.filter(
        status=Subscription.STATUS_NON_RENEWING,
        cancel_at_period_end=True,
        next_payment_at__lte=timezone.now(),
    ).select_related("user")
    for subscription in ended_subscriptions:
        mark_subscription_cancelled(subscription)
        expired += 1
    return expired
