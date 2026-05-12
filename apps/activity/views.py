from rest_framework import generics

from .models import ActivityEvent
from .serializers import ActivityEventSerializer


class ActivityListView(generics.ListAPIView):
    serializer_class = ActivityEventSerializer

    def get_queryset(self):
        return ActivityEvent.objects.filter(owner=self.request.user).select_related("collection", "set", "media_asset")


class RecentActivityListView(ActivityListView):
    def get_queryset(self):
        return super().get_queryset()[:25]


class CollectionActivityListView(ActivityListView):
    def get_queryset(self):
        return super().get_queryset().filter(collection_id=self.kwargs["collection_id"])


class MediaActivityListView(ActivityListView):
    def get_queryset(self):
        return super().get_queryset().filter(media_asset_id=self.kwargs["media_id"])


class FavoriteActivityListView(ActivityListView):
    def get_queryset(self):
        return super().get_queryset().filter(metadata__favorite_list_id=str(self.kwargs["favorite_list_id"]))
