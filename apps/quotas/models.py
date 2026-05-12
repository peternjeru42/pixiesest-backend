from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


class StorageQuota(BaseUUIDModel, TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="storage_quota")
    plan_name = models.CharField(max_length=100, default="starter")
    storage_limit_bytes = models.PositiveBigIntegerField(default=10 * 1024**3)
    storage_used_bytes = models.PositiveBigIntegerField(default=0)
    photo_limit = models.PositiveIntegerField(null=True, blank=True)
    video_limit = models.PositiveIntegerField(null=True, blank=True)
    collection_limit = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} quota"


class StorageUsageLog(BaseUUIDModel):
    CHANGE_CHOICES = (("increase", "Increase"), ("decrease", "Decrease"), ("recalculate", "Recalculate"))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="storage_usage_logs")
    media_asset = models.ForeignKey("media_assets.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True)
    change_type = models.CharField(max_length=20, choices=CHANGE_CHOICES)
    bytes_changed = models.BigIntegerField()
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]
