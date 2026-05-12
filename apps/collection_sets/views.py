from django.db import transaction
from rest_framework import decorators, generics, response, viewsets

from apps.collections.models import Collection
from apps.media_assets.models import MediaAsset
from apps.media_assets.serializers import MediaAssetSerializer

from .models import CollectionSet
from .serializers import CollectionSetSerializer, ReorderSetSerializer, SetCoverSerializer, SetStatsSerializer


class CollectionSetListCreateView(generics.ListCreateAPIView):
    serializer_class = CollectionSetSerializer

    def get_collection(self):
        return Collection.objects.get(id=self.kwargs["collection_id"], owner=self.request.user)

    def get_queryset(self):
        return CollectionSet.objects.filter(collection=self.get_collection()).select_related("cover_asset")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["collection"] = self.get_collection()
        return context


class CollectionSetViewSet(viewsets.ModelViewSet):
    serializer_class = CollectionSetSerializer
    lookup_url_kwarg = "set_id"

    def get_queryset(self):
        return CollectionSet.objects.filter(collection__owner=self.request.user).select_related("collection", "cover_asset")

    def perform_destroy(self, instance):
        instance.delete()

    @decorators.action(detail=True, methods=["post"], url_path="set-cover")
    def set_cover(self, request, set_id=None):
        set_obj = self.get_object()
        serializer = SetCoverSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        set_obj.cover_asset = MediaAsset.objects.get(id=serializer.validated_data["media_asset_id"], owner=request.user)
        set_obj.save(update_fields=["cover_asset", "updated_at"])
        return response.Response(CollectionSetSerializer(set_obj).data)

    @decorators.action(detail=False, methods=["post"])
    def reorder(self, request):
        serializer = ReorderSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            for index, set_id in enumerate(serializer.validated_data["ordered_ids"]):
                CollectionSet.objects.filter(id=set_id, collection__owner=request.user).update(sort_order=index)
        return response.Response({"detail": "Sets reordered."})

    @decorators.action(detail=True, methods=["get"])
    def media(self, request, set_id=None):
        set_obj = self.get_object()
        qs = set_obj.media_assets.filter(owner=request.user).select_related("collection", "set")
        return response.Response(MediaAssetSerializer(qs, many=True, context={"request": request}).data)

    @decorators.action(detail=True, methods=["get"])
    def stats(self, request, set_id=None):
        return response.Response(SetStatsSerializer(self.get_object().stats).data)
