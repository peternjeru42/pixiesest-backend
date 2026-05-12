from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel, SoftDeleteModel, TimeStampedModel


class Collection(BaseUUIDModel, TimeStampedModel, SoftDeleteModel):
    STATUS_CHOICES = (("draft", "Draft"), ("published", "Published"), ("archived", "Archived"))
    VISIBILITY_CHOICES = (
        ("public", "Public"),
        ("password_protected", "Password protected"),
        ("private", "Private"),
        ("unlisted", "Unlisted"),
    )

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="collections")
    folder = models.ForeignKey("folders.Folder", on_delete=models.SET_NULL, null=True, blank=True, related_name="collections")
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=140, db_index=True)
    description = models.TextField(blank=True)
    event_date = models.DateField(null=True, blank=True)
    cover_asset = models.ForeignKey(
        "media_assets.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True, related_name="collection_covers"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft", db_index=True)
    visibility = models.CharField(max_length=30, choices=VISIBILITY_CHOICES, default="private", db_index=True)
    sort_order = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "slug"], condition=models.Q(deleted_at__isnull=True), name="uniq_collection_slug_owner_active")
        ]
        indexes = [models.Index(fields=["owner", "status"]), models.Index(fields=["owner", "sort_order"])]

    def __str__(self):
        return self.title


class CollectionPrivacySettings(BaseUUIDModel, TimeStampedModel):
    collection = models.OneToOneField(Collection, on_delete=models.CASCADE, related_name="privacy_settings")
    is_password_enabled = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=255, blank=True)
    is_client_access_enabled = models.BooleanField(default=False)
    client_password_hash = models.CharField(max_length=255, blank=True)
    require_email_to_view = models.BooleanField(default=False)
    show_on_homepage = models.BooleanField(default=True)
    allow_client_private_marking = models.BooleanField(default=False)


class CollectionDownloadSettings(BaseUUIDModel, TimeStampedModel):
    collection = models.OneToOneField(Collection, on_delete=models.CASCADE, related_name="download_settings")
    photo_download_enabled = models.BooleanField(default=True)
    video_download_enabled = models.BooleanField(default=True)
    single_photo_download_enabled = models.BooleanField(default=True)
    full_gallery_download_enabled = models.BooleanField(default=True)
    favorites_download_enabled = models.BooleanField(default=True)
    download_pin_enabled = models.BooleanField(default=False)
    download_pin_hash = models.CharField(max_length=255, blank=True)
    allow_original_download = models.BooleanField(default=True)
    allow_web_size_download = models.BooleanField(default=True)
    allow_high_res_download = models.BooleanField(default=True)
    web_size_px = models.PositiveIntegerField(default=2048)
    high_res_size_px = models.PositiveIntegerField(default=3600)


class CollectionDesignSettings(BaseUUIDModel, TimeStampedModel):
    collection = models.OneToOneField(Collection, on_delete=models.CASCADE, related_name="design_settings")
    theme = models.CharField(max_length=80, default="minimal")
    layout_style = models.CharField(max_length=80, default="grid")
    cover_style = models.CharField(max_length=80, default="full_bleed")
    grid_style = models.CharField(max_length=80, default="masonry")
    font_family = models.CharField(max_length=120, default="Inter")
    primary_color = models.CharField(max_length=20, default="#111827")
    show_filenames = models.BooleanField(default=False)
    show_media_count = models.BooleanField(default=True)
