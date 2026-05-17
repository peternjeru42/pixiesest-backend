from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.collection_sets.serializers import CollectionSetSerializer
from apps.core.utils import unique_slugify
from apps.folders.models import Folder
from apps.media_assets.models import MediaAsset
from apps.storage.services import get_public_object_url

from .models import Collection, CollectionDesignSettings, CollectionDownloadSettings, CollectionPrivacySettings


class CollectionSerializer(serializers.ModelSerializer):
    download_pin = serializers.CharField(source="download_settings.download_pin", read_only=True)
    cover_url = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()
    sets = serializers.SerializerMethodField()
    folder_id = serializers.PrimaryKeyRelatedField(
        source="folder",
        queryset=Folder.objects.all(),
        write_only=True,
        required=False,
        allow_null=True,
    )
    folder_name = serializers.CharField(source="folder.name", read_only=True)

    class Meta:
        model = Collection
        fields = "__all__"
        read_only_fields = [
            "id",
            "owner",
            "slug",
            "download_pin",
            "folder_name",
            "published_at",
            "created_at",
            "updated_at",
            "deleted_at",
        ]

    def validate_folder(self, folder):
        if folder and folder.owner != self.context["request"].user:
            raise serializers.ValidationError("Folder not found.")
        return folder

    def validate_folder_id(self, folder):
        return self.validate_folder(folder)

    def get_cover_url(self, obj):
        cover_asset = obj.cover_asset or obj.media_assets.order_by("-created_at").first()
        return get_public_object_url(getattr(cover_asset, "thumbnail_file_key", ""))

    def get_counts(self, obj):
        from apps.activity.models import ActivityEvent
        from apps.downloads.models import DownloadLog
        from apps.favorites.models import FavoriteList

        media = obj.media_assets
        return {
            "photos": media.filter(media_type="photo").count(),
            "videos": media.filter(media_type="video").count(),
            "videoDurationSec": 0,
            "favorites": FavoriteList.objects.filter(collection=obj).count(),
            "downloads": DownloadLog.objects.filter(collection=obj).count(),
            "views": ActivityEvent.objects.filter(collection=obj, event_type__icontains="view").count(),
            "sets": obj.sets.count(),
        }

    def get_sets(self, obj):
        return CollectionSetSerializer(obj.sets.all(), many=True).data

    def create(self, validated_data):
        owner = self.context["request"].user
        collection = Collection(owner=owner, **validated_data)
        collection.slug = unique_slugify(collection, collection.title, queryset=Collection.all_objects.filter(owner=owner))
        collection.save()
        return collection


class MoveCollectionSerializer(serializers.Serializer):
    folder_id = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        required=False,
        allow_null=True,
    )
    folder = serializers.PrimaryKeyRelatedField(
        queryset=Folder.objects.all(),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        if "folder_id" not in attrs and "folder" not in attrs:
            raise serializers.ValidationError({"folder_id": "This field is required."})
        folder = attrs.get("folder_id", attrs.get("folder"))
        if folder and folder.owner != self.context["request"].user:
            raise serializers.ValidationError({"folder_id": "Folder not found."})
        attrs["folder"] = folder
        return attrs


class CollectionPrivacySettingsSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    client_password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CollectionPrivacySettings
        exclude = ["password_hash", "client_password_hash"]
        read_only_fields = ["id", "collection", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        client_password = validated_data.pop("client_password", None)
        if password:
            instance.password_hash = make_password(password)
            instance.is_password_enabled = True
        if client_password:
            instance.client_password_hash = make_password(client_password)
            instance.is_client_access_enabled = True
        return super().update(instance, validated_data)


class CollectionDownloadSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionDownloadSettings
        exclude = ["download_pin_hash"]
        read_only_fields = ["id", "collection", "download_pin", "download_pin_enabled", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        validated_data["download_pin_enabled"] = True
        return super().update(instance, validated_data)


class CollectionDesignSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionDesignSettings
        fields = "__all__"
        read_only_fields = ["id", "collection", "created_at", "updated_at"]


class SetCollectionCoverSerializer(serializers.Serializer):
    media_asset_id = serializers.UUIDField()

    def validate_media_asset_id(self, value):
        request = self.context["request"]
        if not MediaAsset.objects.filter(id=value, owner=request.user).exists():
            raise serializers.ValidationError("Media asset not found.")
        return value


class ReorderCollectionSerializer(serializers.Serializer):
    ordered_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
