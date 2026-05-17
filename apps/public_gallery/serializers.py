from rest_framework import serializers

from apps.collection_sets.models import CollectionSet
from apps.collections.models import Collection
from apps.folders.models import Folder
from apps.media_assets.serializers import MediaAssetPublicSerializer
from apps.storage.services import get_public_object_url


class PublicFolderSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    collections_count = serializers.SerializerMethodField()

    class Meta:
        model = Folder
        exclude = ["password_hash", "owner", "deleted_at"]

    def get_cover_url(self, obj):
        return get_public_object_url(getattr(obj.cover_asset, "thumbnail_file_key", ""))

    def get_collections_count(self, obj):
        return obj.collections.filter(status="published").exclude(visibility="private").count()


class PublicCollectionSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        exclude = ["owner", "deleted_at"]

    def get_cover_url(self, obj):
        cover_asset = obj.cover_asset or obj.media_assets.order_by("-created_at").first()
        return get_public_object_url(getattr(cover_asset, "thumbnail_file_key", ""))

    def get_counts(self, obj):
        media = obj.media_assets.filter(status="ready", is_private=False)
        return {
            "photos": media.filter(media_type="photo").count(),
            "videos": media.filter(media_type="video").count(),
            "sets": obj.sets.exclude(visibility="hidden").count(),
        }


class PublicCollectionSetSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    video_duration_sec = serializers.SerializerMethodField()

    class Meta:
        model = CollectionSet
        exclude = ["deleted_at"]

    def get_cover_url(self, obj):
        cover_asset = obj.cover_asset or obj.media_assets.order_by("-created_at").first()
        return get_public_object_url(getattr(cover_asset, "thumbnail_file_key", ""))

    def get_photo_count(self, obj):
        return obj.media_assets.filter(media_type="photo", status="ready", is_private=False).count()

    def get_video_count(self, obj):
        return obj.media_assets.filter(media_type="video", status="ready", is_private=False).count()

    def get_video_duration_sec(self, obj):
        total = 0
        for duration in obj.media_assets.filter(media_type="video", status="ready", is_private=False).values_list("duration_seconds", flat=True):
            total += duration or 0
        return total


PublicMediaAssetSerializer = MediaAssetPublicSerializer
