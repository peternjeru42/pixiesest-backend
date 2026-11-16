from rest_framework import serializers

from .models import BillingPlan, PaymentTransaction, Subscription


class BillingPlanSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    storage_gb = serializers.SerializerMethodField()

    class Meta:
        model = BillingPlan
        fields = [
            "slug",
            "name",
            "amount_minor",
            "price",
            "currency",
            "interval",
            "storage_limit_bytes",
            "storage_gb",
            "features",
            "display_order",
        ]

    def get_price(self, obj):
        return f"{obj.amount_minor / 100:.2f}"

    def get_storage_gb(self, obj):
        return obj.storage_limit_bytes // 1024**3


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = BillingPlanSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "next_payment_at",
            "grace_period_ends_at",
            "cancel_at_period_end",
            "cancelled_at",
            "created_at",
        ]


class PaymentTransactionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source="plan.name", read_only=True)

    class Meta:
        model = PaymentTransaction
        fields = ["id", "reference", "plan_name", "expected_amount_minor", "currency", "status", "paid_at", "created_at"]


class CheckoutSerializer(serializers.Serializer):
    plan = serializers.SlugField()

    def validate_plan(self, value):
        try:
            plan = BillingPlan.objects.get(slug=value, is_active=True)
        except BillingPlan.DoesNotExist as exc:
            raise serializers.ValidationError("Choose a valid plan.") from exc
        if plan.amount_minor == 0:
            raise serializers.ValidationError("The free plan does not require checkout.")
        return plan


class VerifyPaymentSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=100)
