from django.db import models

from apps.core.models import BaseUUIDModel, SoftDeleteModel, TimeStampedModel


class CollectionSet(BaseUUIDModel, TimeStampedModel, SoftDeleteModel):
    VISIBILITY_CHOICES = (("visible_to_all", "Visible to all"), ("client_only", "Client only"), ("hidden", "Hidden"))

    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, related_name="sets")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=140, db_index=True)
    description = models.TextField(blank=True)
    visibility = models.CharField(max_length=30, choices=VISIBILITY_CHOICES, default="visible_to_all", db_index=True)
    cover_asset = models.ForeignKey(
        "media_assets.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True, related_name="set_covers"
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["collection", "slug"], condition=models.Q(deleted_at__isnull=True), name="uniq_set_slug_collection_active")
        ]
        indexes = [models.Index(fields=["collection", "sort_order"])]

    def __str__(self):
        return self.title


class SetStats(BaseUUIDModel, TimeStampedModel):
    set = models.OneToOneField(CollectionSet, on_delete=models.CASCADE, related_name="stats")
    total_photos = models.PositiveIntegerField(default=0)
    total_videos = models.PositiveIntegerField(default=0)
    total_video_duration_seconds = models.PositiveBigIntegerField(default=0)
    total_storage_bytes = models.PositiveBigIntegerField(default=0)
