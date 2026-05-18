from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


class NotificationTemplate(BaseUUIDModel, TimeStampedModel):
    TEMPLATE_CHOICES = (
        ("collection_invite", "Collection invite"),
        ("download_zip_ready", "Download ZIP ready"),
        ("favorite_list_submitted", "Favorite list submitted"),
        ("password_reset", "Password reset"),
        ("email_verification", "Email verification"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="notification_templates")
    template_type = models.CharField(max_length=50, choices=TEMPLATE_CHOICES)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["owner", "template_type"])]


class EmailLog(BaseUUIDModel):
    STATUS_CHOICES = (("queued", "Queued"), ("sent", "Sent"), ("failed", "Failed"))

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="email_logs")
    collection = models.ForeignKey("collections.Collection", on_delete=models.SET_NULL, null=True, blank=True)
    recipient_email = models.EmailField()
    email_type = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["owner", "status", "read_at"]),
        ]
