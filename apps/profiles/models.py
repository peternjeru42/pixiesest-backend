from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


class UserProfile(BaseUUIDModel, TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=255, blank=True)
    business_name = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)
    instagram = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)

    def __str__(self):
        return self.display_name or self.user.email


class UserProfileStats(BaseUUIDModel, TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stats")
    total_photos = models.PositiveIntegerField(default=0)
    total_videos = models.PositiveIntegerField(default=0)
    total_video_duration_seconds = models.PositiveBigIntegerField(default=0)
    total_storage_bytes = models.PositiveBigIntegerField(default=0)
    total_original_storage_bytes = models.PositiveBigIntegerField(default=0)
    total_preview_storage_bytes = models.PositiveBigIntegerField(default=0)
    total_thumbnail_storage_bytes = models.PositiveBigIntegerField(default=0)
    total_collections = models.PositiveIntegerField(default=0)
    total_folders = models.PositiveIntegerField(default=0)
    total_sets = models.PositiveIntegerField(default=0)
    total_favorite_lists = models.PositiveIntegerField(default=0)
    total_downloads = models.PositiveIntegerField(default=0)
    total_gallery_views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Stats for {self.user.email}"
