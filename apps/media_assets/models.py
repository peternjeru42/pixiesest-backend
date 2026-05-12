from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, SoftDeleteModel, TimeStampedModel


class MediaAsset(BaseUUIDModel, TimeStampedModel, SoftDeleteModel):
    MEDIA_TYPE_CHOICES = (("photo", "Photo"), ("video", "Video"), ("gif", "GIF"))
    STATUS_CHOICES = (
        ("uploading", "Uploading"),
        ("uploaded", "Uploaded"),
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
        ("deleted", "Deleted"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="media_assets")
    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, related_name="media_assets")
    set = models.ForeignKey("collection_sets.CollectionSet", on_delete=models.CASCADE, related_name="media_assets")
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, db_index=True)
    original_filename = models.CharField(max_length=255)
    display_filename = models.CharField(max_length=255)
    original_file_key = models.CharField(max_length=500, db_index=True)
    preview_file_key = models.CharField(max_length=500, blank=True)
    thumbnail_file_key = models.CharField(max_length=500, blank=True)
    mime_type = models.CharField(max_length=120)
    extension = models.CharField(max_length=20)
    file_size_bytes = models.PositiveBigIntegerField()
    original_width = models.PositiveIntegerField(null=True, blank=True)
    original_height = models.PositiveIntegerField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="uploading", db_index=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_private = models.BooleanField(default=False)
    is_downloadable = models.BooleanField(default=True)
    is_cover_candidate = models.BooleanField(default=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["collection", "sort_order"]),
            models.Index(fields=["set", "sort_order"]),
        ]

    def __str__(self):
        return self.display_filename


class MediaAssetMetadata(BaseUUIDModel, TimeStampedModel):
    media_asset = models.OneToOneField(MediaAsset, on_delete=models.CASCADE, related_name="metadata")
    camera_make = models.CharField(max_length=120, blank=True)
    camera_model = models.CharField(max_length=120, blank=True)
    lens = models.CharField(max_length=160, blank=True)
    iso = models.PositiveIntegerField(null=True, blank=True)
    aperture = models.CharField(max_length=40, blank=True)
    shutter_speed = models.CharField(max_length=40, blank=True)
    focal_length = models.CharField(max_length=40, blank=True)
    taken_at = models.DateTimeField(null=True, blank=True)
    extra_metadata = models.JSONField(default=dict, blank=True)
