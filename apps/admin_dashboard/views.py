from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import views
from rest_framework.response import Response

from apps.activity.models import ActivityEvent
from apps.collections.models import Collection
from apps.collection_sets.models import CollectionSet
from apps.downloads.models import DownloadLog
from apps.favorites.models import FavoriteList
from apps.folders.models import Folder
from apps.media_assets.models import MediaAsset
from apps.quotas.models import StorageQuota


def _asset_url(key):
    if not key or not settings.CLOUDFLARE_R2_PUBLIC_BASE_URL:
        return ""
    return f"{settings.CLOUDFLARE_R2_PUBLIC_BASE_URL.rstrip('/')}/{key.lstrip('/')}"


def _display_name(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    if full_name:
        return full_name
    try:
        if user.profile.display_name:
            return user.profile.display_name
    except ObjectDoesNotExist:
        pass
    return user.email.split("@", 1)[0]


def _first_name(name):
    return name.split()[0] if name else ""


def _collection_payload(collection):
    media = MediaAsset.objects.filter(collection=collection)
    downloads = DownloadLog.objects.filter(collection=collection).count()
    favorites = FavoriteList.objects.filter(collection=collection).count()
    views = ActivityEvent.objects.filter(collection=collection, event_type__icontains="view").count()
    sets = CollectionSet.objects.filter(collection=collection).count()
    cover_asset = collection.cover_asset or media.order_by("-created_at").first()

    return {
        "id": collection.id,
        "slug": collection.slug,
        "title": collection.title,
        "status": collection.status,
        "cover_url": _asset_url(getattr(cover_asset, "thumbnail_file_key", "")),
        "counts": {
            "photos": media.filter(media_type="photo").count(),
            "videos": media.filter(media_type="video").count(),
            "favorites": favorites,
            "downloads": downloads,
            "views": views,
            "sets": sets,
        },
    }


class DashboardOverviewView(views.APIView):
    def get(self, request):
        user = request.user
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timezone.timedelta(days=7)

        collections = Collection.objects.filter(owner=user)
        media = MediaAsset.objects.filter(owner=user)
        downloads = DownloadLog.objects.filter(collection__owner=user)
        favorites = FavoriteList.objects.filter(collection__owner=user)
        views = ActivityEvent.objects.filter(owner=user, event_type__icontains="view")
        quota = StorageQuota.objects.filter(user=user, is_active=True).first()
        latest_collection = collections.order_by("-created_at").first()

        total_storage_bytes = media.aggregate(total=Sum("file_size_bytes")).get("total") or 0
        total_video_duration_seconds = media.filter(media_type="video").aggregate(total=Sum("duration_seconds")).get("total") or 0
        display_name = _display_name(user)

        return Response(
            {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "display_name": display_name,
                    "first_name": _first_name(display_name),
                },
                "stats": {
                    "photos": media.filter(media_type="photo").count(),
                    "photos_this_month": media.filter(media_type="photo", created_at__gte=month_start).count(),
                    "videos": media.filter(media_type="video").count(),
                    "video_duration_seconds": total_video_duration_seconds,
                    "collections": collections.count(),
                    "published_collections": collections.filter(status="published").count(),
                    "active_collections": collections.exclude(status="archived").count(),
                    "folders": Folder.objects.filter(owner=user).count(),
                    "sets": CollectionSet.objects.filter(collection__owner=user).count(),
                    "favorite_lists": favorites.count(),
                    "pending_favorite_lists": favorites.filter(status="submitted").count(),
                    "downloads": downloads.count(),
                    "downloads_this_week": downloads.filter(created_at__gte=week_start).count(),
                    "gallery_views": views.count(),
                    "gallery_views_this_week": views.filter(created_at__gte=week_start).count(),
                    "storage_used_bytes": total_storage_bytes,
                    "storage_limit_bytes": quota.storage_limit_bytes if quota else 0,
                },
                "recent_uploads": [
                    {
                        "id": asset.id,
                        "filename": asset.display_filename,
                        "media_type": asset.media_type,
                        "status": asset.status,
                        "thumbnail_url": _asset_url(asset.thumbnail_file_key),
                        "created_at": asset.created_at,
                    }
                    for asset in media.order_by("-created_at")[:8]
                ],
                "latest_collection": _collection_payload(latest_collection) if latest_collection else None,
            }
        )


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
