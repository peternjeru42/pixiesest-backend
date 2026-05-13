from rest_framework import serializers

from .models import FavoriteItem, FavoriteList, FavoriteListActivity


class FavoriteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteItem
        fields = "__all__"
        read_only_fields = ["id", "favorite_list", "created_at", "updated_at"]


class FavoriteListSerializer(serializers.ModelSerializer):
    items = FavoriteItemSerializer(many=True, read_only=True)

    class Meta:
        model = FavoriteList
        fields = "__all__"
        read_only_fields = ["id", "collection", "share_token", "submitted_at", "created_at", "updated_at"]


class FavoriteListActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoriteListActivity
        fields = "__all__"
        read_only_fields = [field.name for field in FavoriteListActivity._meta.fields]


class PublicFavoriteCreateSerializer(serializers.Serializer):
    client_email = serializers.EmailField()
    client_name = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)


class FavoriteItemWriteSerializer(serializers.Serializer):
    media_asset_id = serializers.UUIDField()
    note = serializers.CharField(required=False, allow_blank=True)
