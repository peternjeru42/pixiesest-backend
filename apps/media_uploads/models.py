from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


class MediaUploadSession(BaseUUIDModel, TimeStampedModel):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("uploading", "Uploading"),
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="upload_sessions")
    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE)
    set = models.ForeignKey("collection_sets.CollectionSet", on_delete=models.CASCADE)
    media_asset = models.ForeignKey("media_assets.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True)
    upload_id = models.CharField(max_length=120, unique=True, db_index=True)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    file_size_bytes = models.PositiveBigIntegerField()
    r2_object_key = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending", db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["owner", "status"])]
