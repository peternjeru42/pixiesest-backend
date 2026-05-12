from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


class MediaProcessingJob(BaseUUIDModel, TimeStampedModel):
    JOB_TYPE_CHOICES = (
        ("photo_preview", "Photo preview"),
        ("photo_thumbnail", "Photo thumbnail"),
        ("photo_metadata", "Photo metadata"),
        ("video_thumbnail", "Video thumbnail"),
        ("video_metadata", "Video metadata"),
    )
    STATUS_CHOICES = (("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"))

    media_asset = models.ForeignKey("media_assets.MediaAsset", on_delete=models.CASCADE, related_name="processing_jobs")
    job_type = models.CharField(max_length=40, choices=JOB_TYPE_CHOICES, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued", db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "job_type"])]
