from django.db.models import Count, Sum
from rest_framework import views
from rest_framework.response import Response

from apps.activity.models import ActivityEvent
from apps.collections.models import Collection
from apps.collection_sets.models import CollectionSet
from apps.downloads.models import DownloadJob, DownloadLog
from apps.favorites.models import FavoriteList
from apps.folders.models import Folder
from apps.media_assets.models import MediaAsset
from apps.profiles.models import UserProfileStats
from apps.profiles.serializers import UserProfileStatsSerializer


def _stats(user):
    return UserProfileStats.objects.get_or_create(user=user)[0]


class DashboardOverviewView(views.APIView):
    def get(self, request):
        return Response(UserProfileStatsSerializer(_stats(request.user)).data)


class DashboardStorageView(DashboardOverviewView):
    pass


class RecentUploadsView(views.APIView):
    def get(self, request):
        data = list(MediaAsset.objects.filter(owner=request.user).values("id", "display_filename", "media_type", "status", "created_at")[:20])
        return Response(data)


class RecentDownloadsView(views.APIView):
    def get(self, request):
        data = list(DownloadLog.objects.filter(collection__owner=request.user).values("id", "download_type", "client_email", "created_at")[:20])
        return Response(data)


class RecentFavoritesView(views.APIView):
    def get(self, request):
        data = list(FavoriteList.objects.filter(collection__owner=request.user).values("id", "name", "client_email", "status", "created_at")[:20])
        return Response(data)


class RecentActivityView(views.APIView):
    def get(self, request):
        data = list(ActivityEvent.objects.filter(owner=request.user).values("id", "event_type", "actor_type", "actor_email", "created_at")[:30])
        return Response(data)


class CollectionsSummaryView(views.APIView):
    def get(self, request):
        return Response(
            {
                "total": Collection.objects.filter(owner=request.user).count(),
                "by_status": list(Collection.objects.filter(owner=request.user).values("status").annotate(count=Count("id"))),
            }
        )


class MediaSummaryView(views.APIView):
    def get(self, request):
        qs = MediaAsset.objects.filter(owner=request.user)
        return Response(
            {
                "photos": qs.filter(media_type="photo").count(),
                "videos": qs.filter(media_type="video").count(),
                "total_storage_bytes": qs.aggregate(total=Sum("file_size_bytes")).get("total") or 0,
            }
        )


class ClientsSummaryView(views.APIView):
    def get(self, request):
        return Response(
            {
                "favorite_clients": FavoriteList.objects.filter(collection__owner=request.user).values("client_email").distinct().count(),
                "download_clients": DownloadLog.objects.filter(collection__owner=request.user).values("client_email").distinct().count(),
            }
        )
