from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.core.utils import unique_slugify
from apps.media_assets.models import MediaAsset
from apps.storage.services import get_public_object_url

from .models import Folder


class FolderSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()
    collections_count = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, min_length=4)

    class Meta:
        model = Folder
        exclude = ["password_hash"]
        read_only_fields = ["id", "owner", "slug", "created_at", "updated_at", "deleted_at"]

    def get_cover_url(self, obj):
        return get_public_object_url(getattr(obj.cover_asset, "thumbnail_file_key", ""))

    def get_collections_count(self, obj):
        return obj.collections.count()

    def create(self, validated_data):
        password = validated_data.pop("password", "")
        owner = self.context["request"].user
        folder = Folder(owner=owner, **validated_data)
        folder.slug = unique_slugify(folder, folder.name, queryset=Folder.all_objects.filter(owner=owner))
        if password:
            folder.password_hash = make_password(password)
            folder.is_password_enabled = True
        elif folder.is_password_enabled:
            raise serializers.ValidationError({"password": "Password is required when password protection is enabled."})
        folder.save()
        return folder

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        enable_password = validated_data.get("is_password_enabled")
        if password:
            instance.password_hash = make_password(password)
            instance.is_password_enabled = True
        elif enable_password is True and not instance.password_hash:
            raise serializers.ValidationError({"password": "Password is required when password protection is enabled."})
        elif enable_password is False:
            instance.password_hash = ""
        return super().update(instance, validated_data)


class FolderPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=4)


class SetCoverSerializer(serializers.Serializer):
    media_asset_id = serializers.UUIDField()

    def validate_media_asset_id(self, value):
        request = self.context["request"]
        if not MediaAsset.objects.filter(id=value, owner=request.user).exists():
            raise serializers.ValidationError("Media asset not found.")
        return value


class ReorderFolderSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
