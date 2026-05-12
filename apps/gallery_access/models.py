from django.db import models

from apps.core.models import BaseUUIDModel


class GallerySession(BaseUUIDModel):
    ACCESS_CHOICES = (("guest", "Guest"), ("client", "Client"), ("owner_preview", "Owner preview"))

    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, null=True, blank=True)
    folder = models.ForeignKey("folders.Folder", on_delete=models.CASCADE, null=True, blank=True)
    client_email = models.EmailField(blank=True)
    client_name = models.CharField(max_length=255, blank=True)
    access_type = models.CharField(max_length=30, choices=ACCESS_CHOICES, default="guest")
    session_token_hash = models.CharField(max_length=128, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    expires_at = models.DateTimeField(db_index=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["session_token_hash", "expires_at"])]


class AccessAttempt(BaseUUIDModel):
    ATTEMPT_CHOICES = (
        ("collection_password", "Collection password"),
        ("folder_password", "Folder password"),
        ("client_password", "Client password"),
        ("download_pin", "Download PIN"),
    )

    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, null=True, blank=True)
    folder = models.ForeignKey("folders.Folder", on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(blank=True)
    attempt_type = models.CharField(max_length=40, choices=ATTEMPT_CHOICES)
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["collection", "-created_at"]), models.Index(fields=["folder", "-created_at"])]
