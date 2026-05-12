from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response

from apps.collections.models import Collection
from apps.gallery_access.services import has_collection_access
from apps.media_assets.models import MediaAsset

from .models import FavoriteItem, FavoriteList, FavoriteListActivity
from .serializers import FavoriteItemWriteSerializer, FavoriteListSerializer, PublicFavoriteCreateSerializer


def _favorite_activity(favorite_list, activity_type, media_asset=None):
    FavoriteListActivity.objects.create(
        favorite_list=favorite_list,
        media_asset=media_asset,
        activity_type=activity_type,
        client_email=favorite_list.client_email,
    )


class PublicFavoriteCreateView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, collection_slug):
        collection = Collection.objects.get(slug=collection_slug, status="published")
        has_collection_access(request, collection)
        serializer = PublicFavoriteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        fav = FavoriteList.objects.create(collection=collection, **serializer.validated_data)
        _favorite_activity(fav, "created")
        return Response(FavoriteListSerializer(fav).data, status=status.HTTP_201_CREATED)


class PublicFavoriteDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = FavoriteListSerializer
    lookup_field = "share_token"
    queryset = FavoriteList.objects.prefetch_related("items")


class PublicFavoriteItemAddView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, favorite_list_id):
        fav = FavoriteList.objects.select_related("collection").get(id=favorite_list_id, status="active")
        has_collection_access(request, fav.collection)
        serializer = FavoriteItemWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = MediaAsset.objects.get(id=serializer.validated_data["media_asset_id"], collection=fav.collection)
        item, _ = FavoriteItem.objects.update_or_create(
            favorite_list=fav, media_asset=asset, defaults={"note": serializer.validated_data.get("note", "")}
        )
        _favorite_activity(fav, "item_added", asset)
        return Response(FavoriteListSerializer(fav).data, status=status.HTTP_201_CREATED)


class PublicFavoriteItemRemoveView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def delete(self, request, favorite_list_id, media_id):
        fav = FavoriteList.objects.select_related("collection").get(id=favorite_list_id)
        has_collection_access(request, fav.collection)
        FavoriteItem.objects.filter(favorite_list=fav, media_asset_id=media_id).delete()
        _favorite_activity(fav, "item_removed")
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicFavoriteItemNoteView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, favorite_list_id, media_id):
        fav = FavoriteList.objects.select_related("collection").get(id=favorite_list_id)
        has_collection_access(request, fav.collection)
        item = FavoriteItem.objects.get(favorite_list=fav, media_asset_id=media_id)
        item.note = request.data.get("note", "")
        item.save(update_fields=["note", "updated_at"])
        _favorite_activity(fav, "note_updated", item.media_asset)
        return Response(FavoriteListSerializer(fav).data)


class PublicFavoriteSubmitView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, favorite_list_id):
        fav = FavoriteList.objects.select_related("collection").get(id=favorite_list_id)
        has_collection_access(request, fav.collection)
        fav.status = "submitted"
        fav.submitted_at = timezone.now()
        fav.save(update_fields=["status", "submitted_at", "updated_at"])
        _favorite_activity(fav, "submitted")
        return Response(FavoriteListSerializer(fav).data)


class AdminFavoriteListView(generics.ListAPIView):
    serializer_class = FavoriteListSerializer

    def get_queryset(self):
        return FavoriteList.objects.filter(collection_id=self.kwargs["collection_id"], collection__owner=self.request.user).prefetch_related("items")


class AdminFavoriteDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FavoriteListSerializer
    lookup_url_kwarg = "favorite_list_id"

    def get_queryset(self):
        return FavoriteList.objects.filter(collection__owner=self.request.user).prefetch_related("items")


class AdminFavoriteActionView(views.APIView):
    action = None

    def post(self, request, favorite_list_id):
        fav = FavoriteList.objects.get(id=favorite_list_id, collection__owner=request.user)
        if self.action == "lock":
            fav.status = "locked"
            _favorite_activity(fav, "locked")
        elif self.action == "unlock":
            fav.status = "active"
            _favorite_activity(fav, "unlocked")
        elif self.action == "archive":
            fav.status = "archived"
        fav.save(update_fields=["status", "updated_at"])
        return Response(FavoriteListSerializer(fav).data)


class AdminFavoriteExportView(views.APIView):
    def post(self, request, favorite_list_id):
        return Response({"detail": "Favorite export requested."})
