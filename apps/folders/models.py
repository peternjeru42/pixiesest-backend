from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, SoftDeleteModel, TimeStampedModel


class Folder(BaseUUIDModel, TimeStampedModel, SoftDeleteModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="folders")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, db_index=True)
    description = models.TextField(blank=True)
    cover_asset = models.ForeignKey(
        "media_assets.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True, related_name="folder_covers"
    )
    is_password_enabled = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=255, blank=True)
    show_on_homepage = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "slug"], condition=models.Q(deleted_at__isnull=True), name="uniq_folder_slug_owner_active")
        ]
        indexes = [models.Index(fields=["owner", "sort_order"]), models.Index(fields=["owner", "slug"])]

    def __str__(self):
        return self.name
