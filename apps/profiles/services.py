from django.db.models import Sum

from .models import UserProfileStats


def recalculate_user_profile_stats(user):
    from apps.collection_sets.models import CollectionSet
    from apps.collections.models import Collection
    from apps.downloads.models import DownloadLog
    from apps.favorites.models import FavoriteList
    from apps.folders.models import Folder
    from apps.media_assets.models import MediaAsset
    from apps.media_assets.storage import refresh_missing_derived_storage_sizes, storage_totals_for_queryset

    media = MediaAsset.objects.filter(owner=user).exclude(status="deleted")
    refresh_missing_derived_storage_sizes(media)
    storage_totals = storage_totals_for_queryset(media)
    stats = UserProfileStats.objects.get_or_create(user=user)[0]
    stats.total_photos = media.filter(media_type="photo").count()
    stats.total_videos = media.filter(media_type="video").count()
    stats.total_video_duration_seconds = media.aggregate(total=Sum("duration_seconds")).get("total") or 0
    stats.total_original_storage_bytes = storage_totals["original"]
    stats.total_preview_storage_bytes = storage_totals["preview"]
    stats.total_thumbnail_storage_bytes = storage_totals["thumbnail"]
    stats.total_storage_bytes = storage_totals["total"]
    stats.total_collections = Collection.objects.filter(owner=user).count()
    stats.total_folders = Folder.objects.filter(owner=user).count()
    stats.total_sets = CollectionSet.objects.filter(collection__owner=user).count()
    stats.total_favorite_lists = FavoriteList.objects.filter(collection__owner=user).count()
    stats.total_downloads = DownloadLog.objects.filter(collection__owner=user).count()
    stats.total_gallery_views = 0
    stats.save()
    return stats
