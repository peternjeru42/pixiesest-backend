from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.core.utils import unique_slugify
from apps.media_assets.models import MediaAsset

from .models import Collection, CollectionDesignSettings, CollectionDownloadSettings, CollectionPrivacySettings


class CollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        fields = "__all__"
        read_only_fields = ["id", "owner", "slug", "published_at", "created_at", "updated_at", "deleted_at"]

    def validate_folder(self, folder):
        if folder and folder.owner != self.context["request"].user:
            raise serializers.ValidationError("Folder not found.")
        return folder

    def create(self, validated_data):
        owner = self.context["request"].user
        collection = Collection(owner=owner, **validated_data)
        collection.slug = unique_slugify(collection, collection.title, queryset=Collection.all_objects.filter(owner=owner))
        collection.save()
        return collection


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
    download_pin = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = CollectionDownloadSettings
        exclude = ["download_pin_hash"]
        read_only_fields = ["id", "collection", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        pin = validated_data.pop("download_pin", None)
        if pin:
            instance.download_pin_hash = make_password(pin)
            instance.download_pin_enabled = True
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
