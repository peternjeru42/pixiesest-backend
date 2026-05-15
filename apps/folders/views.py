from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q
from rest_framework import decorators, response, status, viewsets

from apps.collections.serializers import CollectionSerializer
from apps.core.permissions import IsOwner
from apps.media_assets.models import MediaAsset

from .models import Folder
from .serializers import FolderPasswordSerializer, FolderSerializer, ReorderFolderSerializer, SetCoverSerializer


class FolderViewSet(viewsets.ModelViewSet):
    serializer_class = FolderSerializer
    permission_classes = [IsOwner]
    lookup_url_kwarg = "folder_id"

    def get_queryset(self):
        queryset = Folder.objects.filter(owner=self.request.user).select_related("cover_asset")
        search = (self.request.query_params.get("search") or self.request.query_params.get("q") or "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        return queryset

    def perform_destroy(self, instance):
        instance.delete()

    @decorators.action(detail=True, methods=["post"], url_path="set-password")
    def set_password(self, request, folder_id=None):
        folder = self.get_object()
        serializer = FolderPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        folder.password_hash = make_password(serializer.validated_data["password"])
        folder.is_password_enabled = True
        folder.save(update_fields=["password_hash", "is_password_enabled", "updated_at"])
        return response.Response({"detail": "Password enabled."})

    @decorators.action(detail=True, methods=["delete"], url_path="remove-password")
    def remove_password(self, request, folder_id=None):
        folder = self.get_object()
        folder.password_hash = ""
        folder.is_password_enabled = False
        folder.save(update_fields=["password_hash", "is_password_enabled", "updated_at"])
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=["post"], url_path="set-cover")
    def set_cover(self, request, folder_id=None):
        folder = self.get_object()
        serializer = SetCoverSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        folder.cover_asset = MediaAsset.objects.get(id=serializer.validated_data["media_asset_id"], owner=request.user)
        folder.save(update_fields=["cover_asset", "updated_at"])
        return response.Response(FolderSerializer(folder).data)

    @decorators.action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        serializer = ReorderFolderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            for index, folder_id in enumerate(serializer.validated_data["ordered_ids"]):
                Folder.objects.filter(id=folder_id, owner=request.user).update(sort_order=index)
        return response.Response({"detail": "Folders reordered."})

    @decorators.action(detail=True, methods=["get"], url_path="collections")
    def collections(self, request, folder_id=None):
        folder = self.get_object()
        qs = folder.collections.filter(owner=request.user).select_related("folder", "cover_asset")
        return response.Response(CollectionSerializer(qs, many=True).data)
