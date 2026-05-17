from rest_framework import serializers

from apps.storage.services import get_public_object_url

from .models import MediaAsset, MediaAssetMetadata


class MediaAssetSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        fields = "__all__"
        read_only_fields = [
            "id",
            "owner",
            "collection",
            "set",
            "original_file_key",
            "preview_file_key",
            "thumbnail_file_key",
            "mime_type",
            "extension",
            "file_size_bytes",
            "checksum",
            "uploaded_at",
            "processed_at",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def get_preview_url(self, obj):
        return get_public_object_url(obj.preview_file_key)

    def get_thumbnail_url(self, obj):
        return get_public_object_url(obj.thumbnail_file_key)


class MediaAssetPublicSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = MediaAsset
        exclude = ["original_file_key", "checksum", "deleted_at", "owner"]
        read_only_fields = [field.name for field in MediaAsset._meta.fields if field.name != "deleted_at"]

    def get_preview_url(self, obj):
        return get_public_object_url(obj.preview_file_key)

    def get_thumbnail_url(self, obj):
        return get_public_object_url(obj.thumbnail_file_key)


class MediaAssetMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAssetMetadata
        fields = "__all__"
        read_only_fields = ["id", "media_asset", "created_at", "updated_at"]


class ReorderMediaSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class MoveMediaSerializer(serializers.Serializer):
    media_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    target_set_id = serializers.UUIDField()


class CopyMediaSerializer(MoveMediaSerializer):
    pass
