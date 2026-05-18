from django.db.models import Sum


def _object_size(key):
    from apps.storage.services import get_object_metadata

    if not key:
        return 0
    try:
        return int(get_object_metadata(key).get("ContentLength") or 0)
    except Exception:
        return 0


def refresh_missing_derived_storage_sizes(queryset):
    for asset in queryset.filter(preview_file_key__gt="", preview_file_size_bytes=0).only(
        "id",
        "preview_file_key",
        "preview_file_size_bytes",
    ):
        size = _object_size(asset.preview_file_key)
        if size:
            asset.preview_file_size_bytes = size
            asset.save(update_fields=["preview_file_size_bytes", "updated_at"])

    for asset in queryset.filter(thumbnail_file_key__gt="", thumbnail_file_size_bytes=0).only(
        "id",
        "thumbnail_file_key",
        "thumbnail_file_size_bytes",
    ):
        size = _object_size(asset.thumbnail_file_key)
        if size:
            asset.thumbnail_file_size_bytes = size
            asset.save(update_fields=["thumbnail_file_size_bytes", "updated_at"])


def storage_totals_for_queryset(queryset):
    totals = queryset.aggregate(
        original=Sum("file_size_bytes"),
        preview=Sum("preview_file_size_bytes"),
        thumbnail=Sum("thumbnail_file_size_bytes"),
    )
    original = totals.get("original") or 0
    preview = totals.get("preview") or 0
    thumbnail = totals.get("thumbnail") or 0
    return {
        "original": original,
        "preview": preview,
        "thumbnail": thumbnail,
        "total": original + preview + thumbnail,
    }


def storage_totals_for_user(user, refresh_missing=False):
    from .models import MediaAsset

    queryset = MediaAsset.objects.filter(owner=user).exclude(status="deleted")
    if refresh_missing:
        refresh_missing_derived_storage_sizes(queryset)
    return storage_totals_for_queryset(queryset)
