import uuid

from django.db import models

from apps.core.models import BaseUUIDModel, TimeStampedModel


def generate_share_token():
    return uuid.uuid4().hex


class FavoriteList(BaseUUIDModel, TimeStampedModel):
    STATUS_CHOICES = (("active", "Active"), ("submitted", "Submitted"), ("locked", "Locked"), ("archived", "Archived"))

    collection = models.ForeignKey("collections.Collection", on_delete=models.CASCADE, related_name="favorite_lists")
    client_email = models.EmailField()
    client_name = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255, default="Favorites")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active", db_index=True)
    selection_limit = models.PositiveIntegerField(null=True, blank=True)
    share_token = models.CharField(max_length=64, unique=True, default=generate_share_token)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["collection", "status"])]


class FavoriteItem(BaseUUIDModel, TimeStampedModel):
    favorite_list = models.ForeignKey(FavoriteList, on_delete=models.CASCADE, related_name="items")
    media_asset = models.ForeignKey("media_assets.MediaAsset", on_delete=models.CASCADE, related_name="favorite_items")
    note = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["favorite_list", "media_asset"], name="uniq_favorite_item")]


class FavoriteListActivity(BaseUUIDModel):
    ACTIVITY_CHOICES = (
        ("created", "Created"),
        ("item_added", "Item added"),
        ("item_removed", "Item removed"),
        ("note_updated", "Note updated"),
        ("submitted", "Submitted"),
        ("locked", "Locked"),
        ("unlocked", "Unlocked"),
    )

    favorite_list = models.ForeignKey(FavoriteList, on_delete=models.CASCADE, related_name="activity")
    media_asset = models.ForeignKey("media_assets.MediaAsset", on_delete=models.SET_NULL, null=True, blank=True)
    activity_type = models.CharField(max_length=40, choices=ACTIVITY_CHOICES)
    client_email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
