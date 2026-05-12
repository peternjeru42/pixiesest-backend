from rest_framework import serializers

from apps.core.utils import unique_slugify
from apps.media_assets.models import MediaAsset

from .models import CollectionSet, SetStats


class CollectionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionSet
        fields = "__all__"
        read_only_fields = ["id", "collection", "slug", "created_at", "updated_at", "deleted_at"]

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
        read_only_fields = fields


class SetCoverSerializer(serializers.Serializer):
    media_asset_id = serializers.UUIDField()

    def validate_media_asset_id(self, value):
        request = self.context["request"]
        if not MediaAsset.objects.filter(id=value, owner=request.user).exists():
            raise serializers.ValidationError("Media asset not found.")
        return value


class ReorderSetSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
