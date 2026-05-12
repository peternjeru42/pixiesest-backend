from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


class DownloadJob(BaseUUIDModel, TimeStampedModel):
    TYPE_CHOICES = (
        ("single_original", "Single original"),
        ("single_web_size", "Single web size"),
        ("single_high_res", "Single high res"),
        ("gallery_original_zip", "Gallery original ZIP"),
        ("gallery_web_size_zip", "Gallery web-size ZIP"),
        ("favorites_original_zip", "Favorites original ZIP"),
        ("favorites_web_size_zip", "Favorites web-size ZIP"),
    )
    QUALITY_CHOICES = (("original", "Original"), ("high_res", "High res"), ("web_size", "Web size"))
    STATUS_CHOICES = (("queued", "Queued"), ("running", "Running"), ("completed", "Completed"), ("failed", "Failed"), ("expired", "Expired"))

    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, related_name="download_jobs")
    favorite_list = models.ForeignKey("favorites.FavoriteList", on_delete=models.SET_NULL, null=True, blank=True)
    requested_by_email = models.EmailField(blank=True)
    download_type = models.CharField(max_length=40, choices=TYPE_CHOICES, db_index=True)
    download_quality = models.CharField(max_length=20, choices=QUALITY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued", db_index=True)
    zip_file_key = models.CharField(max_length=500, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["collection", "status"])]


class DownloadLog(BaseUUIDModel):
    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, related_name="download_logs")
    media_asset = models.ForeignKey("media_assets.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True)
    favorite_list = models.ForeignKey("favorites.FavoriteList", on_delete=models.SET_NULL, null=True, blank=True)
    client_email = models.EmailField(blank=True)
    download_type = models.CharField(max_length=40)
    download_quality = models.CharField(max_length=20)
    file_key_served = models.CharField(max_length=500)
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["collection", "-created_at"])]
