from django.contrib import admin

from .models import BillingCustomer, BillingPlan, PaymentTransaction, Subscription, WebhookEvent


@admin.register(BillingPlan)
class BillingPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "amount_minor", "currency", "interval", "storage_limit_bytes", "is_active")
    list_filter = ("is_active", "currency", "interval")
    search_fields = ("name", "slug", "paystack_test_plan_code", "paystack_live_plan_code")


@admin.register(BillingCustomer)
class BillingCustomerAdmin(admin.ModelAdmin):
    list_display = ("email", "paystack_customer_code", "updated_at")
    search_fields = ("email", "paystack_customer_code", "user__email")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "provider_mode", "next_payment_at", "cancel_at_period_end")
    list_filter = ("status", "provider_mode", "plan")
    search_fields = ("user__email", "paystack_subscription_code", "paystack_customer_code")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "plan", "status", "expected_amount_minor", "currency", "paid_at")
    list_filter = ("status", "currency", "provider_mode", "plan")
    search_fields = ("reference", "user__email")


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "provider_resource_id", "status", "attempts", "created_at", "processed_at")
    list_filter = ("status", "event_type")
    search_fields = ("fingerprint", "provider_resource_id")
