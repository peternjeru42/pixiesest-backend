from django.urls import path

from .views import (
    BillingSummaryView,
    CancelSubscriptionView,
    CheckoutView,
    PaymentMethodView,
    PaystackWebhookView,
    PlanListView,
    ResumeSubscriptionView,
    VerifyPaymentView,
)

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="billing-plans"),
    path("summary/", BillingSummaryView.as_view(), name="billing-summary"),
    path("checkout/", CheckoutView.as_view(), name="billing-checkout"),
    path("verify/", VerifyPaymentView.as_view(), name="billing-verify"),
    path("subscription/cancel/", CancelSubscriptionView.as_view(), name="billing-cancel"),
    path("subscription/resume/", ResumeSubscriptionView.as_view(), name="billing-resume"),
    path("subscription/payment-method/", PaymentMethodView.as_view(), name="billing-payment-method"),
    path("webhooks/paystack/", PaystackWebhookView.as_view(), name="paystack-webhook"),
]
