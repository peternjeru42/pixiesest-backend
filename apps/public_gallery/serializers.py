from rest_framework import serializers

from apps.collection_sets.models import CollectionSet
from apps.collections.models import Collection
from apps.folders.models import Folder
from apps.media_assets.serializers import MediaAssetPublicSerializer


class PublicFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Folder
        exclude = ["password_hash", "owner", "deleted_at"]


class PublicCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collection
        exclude = ["owner", "deleted_at"]


class PublicCollectionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionSet
        exclude = ["deleted_at"]


PublicMediaAssetSerializer = MediaAssetPublicSerializer
