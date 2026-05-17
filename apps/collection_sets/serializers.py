from django.db.models import Sum
from rest_framework import serializers

from apps.core.utils import unique_slugify
from apps.media_assets.models import MediaAsset
from apps.storage.services import get_public_object_url

from .models import CollectionSet, SetStats


class CollectionSetSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()
    video_count = serializers.SerializerMethodField()
    video_duration_sec = serializers.SerializerMethodField()

    class Meta:
        model = CollectionSet
        fields = "__all__"
        read_only_fields = ["id", "collection", "slug", "created_at", "updated_at", "deleted_at"]

    def get_cover_url(self, obj):
        cover_asset = obj.cover_asset or obj.media_assets.order_by("-created_at").first()
        return get_public_object_url(getattr(cover_asset, "thumbnail_file_key", ""))

    def get_photo_count(self, obj):
        return obj.media_assets.filter(media_type="photo").count()

    def get_video_count(self, obj):
        return obj.media_assets.filter(media_type="video").count()

    def get_video_duration_sec(self, obj):
        return obj.media_assets.filter(media_type="video").aggregate(total=Sum("duration_seconds")).get("total") or 0

    def create(self, validated_data):
        collection = self.context["collection"]
        instance = CollectionSet(collection=collection, **validated_data)
        instance.slug = unique_slugify(instance, instance.title, queryset=CollectionSet.all_objects.filter(collection=collection))
        instance.save()
        return instance


class SetStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SetStats
        fields = "__all__"
        read_only_fields = [field.name for field in SetStats._meta.fields]


class SetCoverSerializer(serializers.Serializer):
    media_asset_id = serializers.UUIDField()

    def validate_media_asset_id(self, value):
        request = self.context["request"]
        if not MediaAsset.objects.filter(id=value, owner=request.user).exists():
            raise serializers.ValidationError("Media asset not found.")
        return value


class ReorderSetSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
