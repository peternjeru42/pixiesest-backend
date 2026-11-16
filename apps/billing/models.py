from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


class BillingPlan(BaseUUIDModel, TimeStampedModel):
    slug = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    amount_minor = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    interval = models.CharField(max_length=16, default="monthly")
    storage_limit_bytes = models.PositiveBigIntegerField()
    features = models.JSONField(default=list, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    paystack_test_plan_code = models.CharField(max_length=64, blank=True)
    paystack_live_plan_code = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["display_order", "amount_minor"]

    def __str__(self):
        return self.name


class BillingCustomer(BaseUUIDModel, TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_customer",
    )
    email = models.EmailField()
    paystack_customer_code = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return self.email


class Subscription(BaseUUIDModel, TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_NON_RENEWING = "non_renewing"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_NON_RENEWING, "Non-renewing"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(BillingPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    provider_mode = models.CharField(max_length=8, default="test")
    paystack_subscription_code = models.CharField(max_length=64, null=True, blank=True, unique=True)
    paystack_email_token = models.CharField(max_length=128, blank=True)
    paystack_customer_code = models.CharField(max_length=64, blank=True, db_index=True)
    next_payment_at = models.DateTimeField(null=True, blank=True)
    grace_period_ends_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "status"])]

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"


class PaymentTransaction(BaseUUIDModel, TimeStampedModel):
    STATUS_INITIALIZED = "initialized"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_ABANDONED = "abandoned"
    STATUS_CHOICES = (
        (STATUS_INITIALIZED, "Initialized"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_ABANDONED, "Abandoned"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="billing_transactions")
    plan = models.ForeignKey(BillingPlan, on_delete=models.PROTECT, related_name="transactions")
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    reference = models.CharField(max_length=100, unique=True)
    provider_mode = models.CharField(max_length=8, default="test")
    provider_transaction_id = models.BigIntegerField(null=True, blank=True)
    expected_amount_minor = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_INITIALIZED, db_index=True)
    channel = models.CharField(max_length=32, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    provider_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return self.reference


class WebhookEvent(BaseUUIDModel, TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_PROCESSED, "Processed"),
        (STATUS_FAILED, "Failed"),
    )

    fingerprint = models.CharField(max_length=64, unique=True)
    event_type = models.CharField(max_length=64, db_index=True)
    provider_resource_id = models.CharField(max_length=128, blank=True, db_index=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} ({self.status})"
