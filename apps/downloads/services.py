from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.utils import timezone

from apps.core.exceptions import GalleryAccessDenied
from apps.gallery_access.services import get_gallery_session, has_collection_access
from apps.media_assets.models import MediaAsset
from apps.storage.services import generate_presigned_download_url

from .models import DownloadJob, DownloadLog


def _request_meta(request):
    return {
        "ip_address": request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0] or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
    }


def validate_download_access(request, collection, *, quality, media_asset=None, pin=""):
    has_collection_access(request, collection)
    settings = collection.download_settings
    if media_asset and not media_asset.is_downloadable:
        raise GalleryAccessDenied("Media is not downloadable.")
    if quality == "original" and not settings.allow_original_download:
        raise GalleryAccessDenied("Original downloads are disabled.")
    if quality == "web_size" and not settings.allow_web_size_download:
        raise GalleryAccessDenied("Web-size downloads are disabled.")
    if quality == "high_res" and not settings.allow_high_res_download:
        raise GalleryAccessDenied("High-res downloads are disabled.")
    if settings.download_pin_enabled and not check_password(pin, settings.download_pin_hash):
        raise GalleryAccessDenied("Valid download PIN required.")
    return True


def signed_single_download(request, media_asset, quality, pin=""):
    validate_download_access(request, media_asset.collection, quality=quality, media_asset=media_asset, pin=pin)
    if quality == "original":
        key = media_asset.original_file_key
        download_type = "single_original"
    elif quality == "high_res":
        key = media_asset.preview_file_key
        download_type = "single_high_res"
    else:
        key = media_asset.preview_file_key
        download_type = "single_web_size"
    session = get_gallery_session(request)
    DownloadLog.objects.create(
        collection=media_asset.collection,
        media_asset=media_asset,
        client_email=session.client_email if session else "",
        download_type=download_type,
        download_quality=quality,
        file_key_served=key,
        file_size_bytes=media_asset.file_size_bytes if quality == "original" else None,
        **_request_meta(request),
    )
    return generate_presigned_download_url(key, media_asset.original_filename)


def create_zip_job(request, collection, download_type, quality, favorite_list=None, pin=""):
    validate_download_access(request, collection, quality=quality, pin=pin)
    session = get_gallery_session(request)
    job = DownloadJob.objects.create(
        collection=collection,
        favorite_list=favorite_list,
        requested_by_email=session.client_email if session else "",
        download_type=download_type,
        download_quality=quality,
        status="queued",
        expires_at=timezone.now() + timedelta(days=2),
    )
    DownloadLog.objects.create(
        collection=collection,
        favorite_list=favorite_list,
        client_email=job.requested_by_email,
        download_type=download_type,
        download_quality=quality,
        file_key_served="pending_zip",
        **_request_meta(request),
    )
    return job


def get_downloadable_assets_for_job(job):
    qs = MediaAsset.objects.filter(collection=job.collection, status="ready", is_downloadable=True)
    if job.favorite_list_id:
        qs = qs.filter(favorite_items__favorite_list=job.favorite_list)
    return qs.order_by("sort_order", "created_at")
