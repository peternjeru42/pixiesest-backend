from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, views
from rest_framework.response import Response

from apps.collection_sets.models import CollectionSet
from apps.collections.models import Collection
from apps.folders.models import Folder
from apps.gallery_access.services import get_gallery_session, has_collection_access, has_folder_access
from apps.media_assets.models import MediaAsset
from apps.storage.services import generate_presigned_download_url

from .serializers import (
    PublicCollectionSerializer,
    PublicCollectionSetSerializer,
    PublicFolderSerializer,
    PublicMediaAssetSerializer,
)


class PublicBase:
    permission_classes = [permissions.AllowAny]


def _has_client_access(request, collection):
    session = get_gallery_session(request)
    return bool(session and session.access_type == "client" and session.collection_id == collection.id)


class PublicFolderDetailView(PublicBase, generics.RetrieveAPIView):
    serializer_class = PublicFolderSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "folder_slug"
    queryset = Folder.objects.all()

    def get_object(self):
        obj = super().get_object()
        has_folder_access(self.request, obj)
        return obj


class PublicFolderCollectionsView(PublicBase, generics.ListAPIView):
    serializer_class = PublicCollectionSerializer

    def get_queryset(self):
        folder = get_object_or_404(Folder, slug=self.kwargs["folder_slug"])
        has_folder_access(self.request, folder)
        return Collection.objects.filter(folder=folder, status="published").exclude(visibility="private")


class PublicCollectionDetailView(PublicBase, generics.RetrieveAPIView):
    serializer_class = PublicCollectionSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "collection_slug"

    def get_queryset(self):
        return Collection.objects.filter(status="published").select_related("privacy_settings", "download_settings", "design_settings")

    def get_object(self):
        obj = super().get_object()
        has_collection_access(self.request, obj)
        return obj


class PublicCollectionSetsView(PublicBase, generics.ListAPIView):
    serializer_class = PublicCollectionSetSerializer

    def get_queryset(self):
        collection = Collection.objects.get(slug=self.kwargs["collection_slug"], status="published")
        has_collection_access(self.request, collection)
        queryset = CollectionSet.objects.filter(collection=collection).exclude(visibility="hidden")
        if not _has_client_access(self.request, collection):
            queryset = queryset.exclude(visibility="client_only")
        return queryset


class PublicCollectionMediaView(PublicBase, generics.ListAPIView):
    serializer_class = PublicMediaAssetSerializer

    def get_queryset(self):
        collection = Collection.objects.get(slug=self.kwargs["collection_slug"], status="published")
        has_collection_access(self.request, collection)
        queryset = MediaAsset.objects.filter(collection=collection, status="ready", is_private=False).exclude(set__visibility="hidden")
        if not _has_client_access(self.request, collection):
            queryset = queryset.exclude(set__visibility="client_only")
        return queryset.select_related("collection", "set")


class PublicSetDetailView(PublicBase, generics.RetrieveAPIView):
    serializer_class = PublicCollectionSetSerializer
    lookup_field = "slug"
    lookup_url_kwarg = "set_slug"
    queryset = CollectionSet.objects.select_related("collection")

    def get_object(self):
        obj = super().get_object()
        has_collection_access(self.request, obj.collection, require_client=obj.visibility == "client_only")
        return obj


class PublicSetMediaView(PublicBase, generics.ListAPIView):
    serializer_class = PublicMediaAssetSerializer

    def get_queryset(self):
        set_obj = CollectionSet.objects.select_related("collection").get(slug=self.kwargs["set_slug"])
        has_collection_access(self.request, set_obj.collection, require_client=set_obj.visibility == "client_only")
        return MediaAsset.objects.filter(set=set_obj, status="ready", is_private=False)


class PublicMediaDetailView(PublicBase, generics.RetrieveAPIView):
    serializer_class = PublicMediaAssetSerializer
    lookup_url_kwarg = "media_id"
    queryset = MediaAsset.objects.filter(status="ready", is_private=False).exclude(set__visibility="hidden").select_related("collection", "set")

    def get_object(self):
        obj = super().get_object()
        has_collection_access(self.request, obj.collection, require_client=bool(obj.set and obj.set.visibility == "client_only"))
        return obj


class PublicMediaSignedUrlView(PublicBase, views.APIView):
    key_name = "preview_file_key"

    def get(self, request, media_id):
        asset = MediaAsset.objects.exclude(set__visibility="hidden").select_related("collection", "set").get(id=media_id, status="ready", is_private=False)
        has_collection_access(request, asset.collection, require_client=bool(asset.set and asset.set.visibility == "client_only"))
        key = getattr(asset, self.key_name)
        return Response({"url": generate_presigned_download_url(key) if key else None})


class PublicMediaThumbnailUrlView(PublicMediaSignedUrlView):
    key_name = "thumbnail_file_key"
