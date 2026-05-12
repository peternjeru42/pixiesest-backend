from django.conf import settings
from django.db import models

from apps.core.models import BaseUUIDModel


class ActivityEvent(BaseUUIDModel):
    ACTOR_CHOICES = (("owner", "Owner"), ("client", "Client"), ("system", "System"))

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_events")
    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, null=True, blank=True)
    set = models.ForeignKey("collection_sets.CollectionSet", on_delete=models.CASCADE, null=True, blank=True)
    media_asset = models.ForeignKey("media_assets.MediaAsset", on_delete=models.CASCADE, null=True, blank=True)
    event_type = models.CharField(max_length=80, db_index=True)
    actor_type = models.CharField(max_length=20, choices=ACTOR_CHOICES, default="system")
    actor_email = models.EmailField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
            models.Index(fields=["collection", "-created_at"]),
            models.Index(fields=["media_asset", "-created_at"]),
        ]
