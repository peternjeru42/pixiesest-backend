from django.db import transaction
from rest_framework import decorators, response, status, viewsets
from rest_framework.generics import get_object_or_404

from apps.core.permissions import IsOwner
from apps.media_assets.models import MediaAsset

from .models import Collection
from .serializers import (
    CollectionDesignSettingsSerializer,
    CollectionDownloadSettingsSerializer,
    MoveCollectionSerializer,
    CollectionPrivacySettingsSerializer,
    CollectionSerializer,
    ReorderCollectionSerializer,
    SetCollectionCoverSerializer,
)
from .services import delete_collection, duplicate_collection, publish_collection


class CollectionViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSerializer
    permission_classes = [IsOwner]
    lookup_url_kwarg = "collection_id"

    def get_queryset(self):
        return Collection.objects.filter(owner=self.request.user).select_related("folder", "cover_asset", "download_settings")

    def perform_destroy(self, instance):
        delete_collection(instance)

    @decorators.action(detail=True, methods=["post"])
    def publish(self, request, collection_id=None):
        return response.Response(CollectionSerializer(publish_collection(self.get_object())).data)

    @decorators.action(detail=True, methods=["post"])
    def unpublish(self, request, collection_id=None):
        collection = self.get_object()
        collection.status = "draft"
        collection.save(update_fields=["status", "updated_at"])
        return response.Response(CollectionSerializer(collection).data)

    @decorators.action(detail=True, methods=["post"])
    def archive(self, request, collection_id=None):
        collection = self.get_object()
        collection.status = "archived"
        collection.save(update_fields=["status", "updated_at"])
        return response.Response(CollectionSerializer(collection).data)

    @decorators.action(detail=True, methods=["post"])
    def restore(self, request, collection_id=None):
        collection = Collection.all_objects.get(id=collection_id, owner=request.user)
        collection.restore()
        return response.Response(CollectionSerializer(collection).data)

    @decorators.action(detail=True, methods=["post"])
    def duplicate(self, request, collection_id=None):
        return response.Response(CollectionSerializer(duplicate_collection(self.get_object(), request.user)).data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post", "patch"])
    def move(self, request, collection_id=None):
        collection = self.get_object()
        serializer = MoveCollectionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        collection.folder = serializer.validated_data["folder"]
        collection.save(update_fields=["folder", "updated_at"])
        return response.Response(CollectionSerializer(collection).data)

    @decorators.action(detail=True, methods=["post"], url_path="set-cover")
    def set_cover(self, request, collection_id=None):
        collection = self.get_object()
        serializer = SetCollectionCoverSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        collection.cover_asset = MediaAsset.objects.get(id=serializer.validated_data["media_asset_id"], owner=request.user)
        collection.save(update_fields=["cover_asset", "updated_at"])
        return response.Response(CollectionSerializer(collection).data)

    @decorators.action(detail=False, methods=["post"])
    def reorder(self, request):
        serializer = ReorderCollectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            for index, collection_id in enumerate(serializer.validated_data["ordered_ids"]):
                Collection.objects.filter(id=collection_id, owner=request.user).update(sort_order=index)
        return response.Response({"detail": "Collections reordered."})

    @decorators.action(detail=True, methods=["get"])
    def summary(self, request, collection_id=None):
        collection = self.get_object()
        return response.Response(
            {
                "id": collection.id,
                "title": collection.title,
                "status": collection.status,
                "media_count": collection.media_assets.count(),
                "sets_count": collection.sets.count(),
            }
        )

    @decorators.action(detail=True, methods=["get"])
    def stats(self, request, collection_id=None):
        collection = self.get_object()
        return response.Response({"photos": collection.media_assets.filter(media_type="photo").count(), "videos": collection.media_assets.filter(media_type="video").count()})

    @decorators.action(detail=True, methods=["get", "patch"])
    def privacy(self, request, collection_id=None):
        settings = self.get_object().privacy_settings
        serializer = CollectionPrivacySettingsSerializer(settings, data=request.data, partial=True) if request.method == "PATCH" else CollectionPrivacySettingsSerializer(settings)
        if request.method == "PATCH":
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["get", "patch"], url_path="downloads/settings")
    def download_settings(self, request, collection_id=None):
        settings = self.get_object().download_settings
        serializer = CollectionDownloadSettingsSerializer(settings, data=request.data, partial=True) if request.method == "PATCH" else CollectionDownloadSettingsSerializer(settings)
        if request.method == "PATCH":
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["get", "patch"])
    def design(self, request, collection_id=None):
        settings = self.get_object().design_settings
        serializer = CollectionDesignSettingsSerializer(settings, data=request.data, partial=True) if request.method == "PATCH" else CollectionDesignSettingsSerializer(settings)
        if request.method == "PATCH":
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return response.Response(serializer.data)
