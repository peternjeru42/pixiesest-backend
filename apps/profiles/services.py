from django.db.models import Sum

from .models import UserProfileStats


def recalculate_user_profile_stats(user):
    from apps.collection_sets.models import CollectionSet
    from apps.collections.models import Collection
    from apps.downloads.models import DownloadLog
    from apps.favorites.models import FavoriteList
    from apps.folders.models import Folder
    from apps.media_assets.models import MediaAsset

    media = MediaAsset.objects.filter(owner=user).exclude(status="deleted")
    stats = UserProfileStats.objects.get_or_create(user=user)[0]
    stats.total_photos = media.filter(media_type="photo").count()
    stats.total_videos = media.filter(media_type="video").count()
    stats.total_video_duration_seconds = media.aggregate(total=Sum("duration_seconds")).get("total") or 0
    stats.total_original_storage_bytes = media.aggregate(total=Sum("file_size_bytes")).get("total") or 0
    stats.total_preview_storage_bytes = 0
    stats.total_thumbnail_storage_bytes = 0
    stats.total_storage_bytes = (
        stats.total_original_storage_bytes + stats.total_preview_storage_bytes + stats.total_thumbnail_storage_bytes
    )
    stats.total_collections = Collection.objects.filter(owner=user).count()
    stats.total_folders = Folder.objects.filter(owner=user).count()
    stats.total_sets = CollectionSet.objects.filter(collection__owner=user).count()
    stats.total_favorite_lists = FavoriteList.objects.filter(collection__owner=user).count()
    stats.total_downloads = DownloadLog.objects.filter(collection__owner=user).count()
    stats.total_gallery_views = 0
    stats.save()
    return stats
