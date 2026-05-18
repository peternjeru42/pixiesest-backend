from django.db import transaction
from rest_framework import decorators, generics, response, viewsets

from apps.collection_sets.models import CollectionSet
from apps.collections.models import Collection
from apps.storage.services import generate_presigned_download_url

from .models import MediaAsset, MediaAssetMetadata
from .serializers import (
    CopyMediaSerializer,
    MediaAssetMetadataSerializer,
    MediaAssetSerializer,
    MoveMediaSerializer,
    ReorderMediaSerializer,
)


class MediaAssetViewSet(viewsets.ModelViewSet):
    serializer_class = MediaAssetSerializer
    lookup_url_kwarg = "media_id"

    def get_queryset(self):
        return MediaAsset.objects.filter(owner=self.request.user).select_related("collection", "set")

    def perform_destroy(self, instance):
        instance.status = "deleted"
        instance.delete()

    @decorators.action(detail=False, methods=["post"])
    def reorder(self, request):
        serializer = ReorderMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            for index, media_id in enumerate(serializer.validated_data["ordered_ids"]):
                MediaAsset.objects.filter(id=media_id, owner=request.user).update(sort_order=index)
        return response.Response({"detail": "Media reordered."})

    @decorators.action(detail=False, methods=["post"])
    def move(self, request):
        serializer = MoveMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_set = CollectionSet.objects.get(id=serializer.validated_data["target_set_id"], collection__owner=request.user)
        MediaAsset.objects.filter(id__in=serializer.validated_data["media_ids"], owner=request.user).update(
            collection=target_set.collection, set=target_set
        )
        return response.Response({"detail": "Media moved."})

    @decorators.action(detail=False, methods=["post"])
    def copy(self, request):
        serializer = CopyMediaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_set = CollectionSet.objects.get(id=serializer.validated_data["target_set_id"], collection__owner=request.user)
        copies = []
        for asset in MediaAsset.objects.filter(id__in=serializer.validated_data["media_ids"], owner=request.user):
            asset.pk = None
            asset.collection = target_set.collection
            asset.set = target_set
            asset.save()
            copies.append(asset)
        return response.Response(MediaAssetSerializer(copies, many=True).data)

    @decorators.action(detail=True, methods=["patch"])
    def privacy(self, request, media_id=None):
        asset = self.get_object()
        asset.is_private = bool(request.data.get("is_private", asset.is_private))
        asset.save(update_fields=["is_private", "updated_at"])
        return response.Response(MediaAssetSerializer(asset).data)

    @decorators.action(detail=True, methods=["patch"])
    def downloadable(self, request, media_id=None):
        asset = self.get_object()
        asset.is_downloadable = bool(request.data.get("is_downloadable", asset.is_downloadable))
        asset.save(update_fields=["is_downloadable", "updated_at"])
        return response.Response(MediaAssetSerializer(asset).data)

    @decorators.action(detail=True, methods=["get"], url_path="download-url")
    def download_url(self, request, media_id=None):
        asset = self.get_object()
        return response.Response(
            {
                "url": generate_presigned_download_url(asset.original_file_key, asset.original_filename),
                "filename": asset.original_filename,
            }
        )

    @decorators.action(detail=True, methods=["get", "patch"])
    def metadata(self, request, media_id=None):
        metadata = MediaAssetMetadata.objects.get_or_create(media_asset=self.get_object())[0]
        serializer = MediaAssetMetadataSerializer(metadata, data=request.data, partial=True) if request.method == "PATCH" else MediaAssetMetadataSerializer(metadata)
        if request.method == "PATCH":
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return response.Response(serializer.data)

    @decorators.action(detail=True, methods=["post"])
    def reprocess(self, request, media_id=None):
        from apps.media_processing.tasks import process_uploaded_media

        process_uploaded_media.delay(str(self.get_object().id))
        return response.Response({"detail": "Media queued for reprocessing."})


class CollectionMediaListView(generics.ListAPIView):
    serializer_class = MediaAssetSerializer

    def get_queryset(self):
        collection = Collection.objects.get(id=self.kwargs["collection_id"], owner=self.request.user)
        return MediaAsset.objects.filter(collection=collection, owner=self.request.user).select_related("collection", "set")


class SetMediaListView(generics.ListAPIView):
    serializer_class = MediaAssetSerializer

    def get_queryset(self):
        set_obj = CollectionSet.objects.get(id=self.kwargs["set_id"], collection__owner=self.request.user)
        return MediaAsset.objects.filter(set=set_obj, owner=self.request.user).select_related("collection", "set")
