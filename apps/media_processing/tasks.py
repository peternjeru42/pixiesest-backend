import io
import logging
import tempfile
from functools import lru_cache
from pathlib import Path

import ffmpeg
import redis
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from PIL import Image, ExifTags, ImageOps

from apps.media_assets.models import MediaAsset, MediaAssetMetadata
from apps.profiles.services import recalculate_user_profile_stats
from apps.quotas.services import recalculate_storage_usage
from apps.storage.services import build_preview_key, build_thumbnail_key, download_bytes, download_to_file, upload_bytes

from .models import MediaProcessingJob

logger = logging.getLogger(__name__)
STATS_REFRESH_DELAY_SECONDS = 10
STATS_REFRESH_LOCK_SECONDS = 60 * 60


@lru_cache(maxsize=1)
def _redis_client():
    return redis.Redis.from_url(settings.CELERY_BROKER_URL)


def _stats_refresh_key(owner_id):
    return f"media-processing:stats-refresh:{owner_id}"


def schedule_owner_stats_refresh(owner_id):
    key = _stats_refresh_key(owner_id)
    try:
        should_schedule = bool(
            _redis_client().set(key, "1", nx=True, ex=STATS_REFRESH_LOCK_SECONDS)
        )
    except Exception:
        logger.exception("Unable to debounce owner statistics refresh.", extra={"owner_id": str(owner_id)})
        should_schedule = True
    if should_schedule:
        try:
            refresh_owner_stats.apply_async(args=[str(owner_id)], countdown=STATS_REFRESH_DELAY_SECONDS)
        except Exception:
            logger.exception("Unable to enqueue owner statistics refresh.", extra={"owner_id": str(owner_id)})
            try:
                _redis_client().delete(key)
            except Exception:
                logger.exception("Unable to clear unscheduled statistics refresh lock.", extra={"owner_id": str(owner_id)})


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def refresh_owner_stats(owner_id):
    key = _stats_refresh_key(owner_id)
    try:
        _redis_client().delete(key)
    except Exception:
        logger.exception("Unable to clear owner statistics refresh lock.", extra={"owner_id": str(owner_id)})
    user = get_user_model().objects.get(id=owner_id)
    recalculate_storage_usage(user)
    recalculate_user_profile_stats(user)


def _required_job_types(asset):
    if asset.media_type in {"photo", "gif"}:
        return {"photo_preview", "photo_thumbnail", "photo_metadata"}
    return {"video_thumbnail", "video_metadata"}


def _job(asset, job_type):
    job = MediaProcessingJob.objects.create(media_asset=asset, job_type=job_type, status="running", started_at=timezone.now())
    job.attempts += 1
    job.save(update_fields=["attempts", "status", "started_at", "updated_at"])
    return job


def _complete(job):
    job.status = "completed"
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "completed_at", "updated_at"])


def _fail(job, exc):
    job.status = "failed"
    job.error_message = str(exc)
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
    _mark_asset_processing_failed(job.media_asset_id)


def _mark_asset_processing_failed(media_asset_id):
    asset = MediaAsset.objects.filter(id=media_asset_id).first()
    if not asset:
        return
    asset.status = "failed"
    asset.save(update_fields=["status", "updated_at"])
    _update_upload_session(asset, "failed")


def _finish_asset_if_processing_complete(media_asset_id):
    with transaction.atomic():
        asset = MediaAsset.objects.select_for_update().select_related("owner").get(id=media_asset_id)
        if asset.status != "processing":
            return

        required_job_types = _required_job_types(asset)
        completed_job_types = set(
            MediaProcessingJob.objects.filter(
                media_asset=asset,
                job_type__in=required_job_types,
                status="completed",
            ).values_list("job_type", flat=True)
        )
        if completed_job_types != required_job_types:
            return

        asset.status = "ready"
        asset.processed_at = timezone.now()
        asset.save(update_fields=["status", "processed_at", "updated_at"])
        _update_upload_session(asset, "completed")
        transaction.on_commit(lambda owner_id=asset.owner_id: schedule_owner_stats_refresh(owner_id))


@shared_task
def process_uploaded_media(media_asset_id):
    asset = MediaAsset.objects.select_related("owner", "collection", "set").get(id=media_asset_id)
    try:
        asset.status = "processing"
        asset.processed_at = None
        asset.save(update_fields=["status", "processed_at", "updated_at"])
        MediaProcessingJob.objects.filter(media_asset=asset, job_type__in=_required_job_types(asset)).delete()
        if asset.media_type in {"photo", "gif"}:
            process_photo_media(str(asset.id))
        else:
            process_video_media(str(asset.id))
        return str(asset.id)
    except Exception:
        logger.exception("Media processing failed.", extra={"media_asset_id": str(asset.id)})
        _mark_asset_processing_failed(asset.id)
        raise


def _update_upload_session(asset, status):
    from apps.media_uploads.models import MediaUploadSession

    MediaUploadSession.objects.filter(media_asset=asset).update(status=status, updated_at=timezone.now())


def _save_webp_variant(image, size, quality, key):
    variant = image.copy()
    variant.thumbnail(size)
    out = io.BytesIO()
    variant.convert("RGB").save(out, format="WEBP", quality=quality)
    body = out.getvalue()
    upload_bytes(key, body, "image/webp")
    return len(body)


def _load_image_from_storage(key, extension):
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / f"source.{extension or 'jpg'}"
        download_to_file(key, source_path)
        with Image.open(source_path) as source:
            return ImageOps.exif_transpose(source)


def _video_rotation_degrees(video_stream):
    rotate_tag = video_stream.get("tags", {}).get("rotate")
    if rotate_tag not in {None, ""}:
        try:
            return int(float(rotate_tag))
        except (TypeError, ValueError):
            pass

    for side_data in video_stream.get("side_data_list", []):
        rotation = side_data.get("rotation")
        if rotation not in {None, ""}:
            try:
                return int(float(rotation))
            except (TypeError, ValueError):
                pass
    return 0


def _video_display_dimensions(video_stream):
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    rotation = abs(_video_rotation_degrees(video_stream)) % 180
    if rotation == 90:
        return height, width
    return width, height


@shared_task
def process_photo_media(media_asset_id):
    asset = MediaAsset.objects.select_related("owner", "collection").get(id=media_asset_id)
    jobs = {
        "photo_preview": _job(asset, "photo_preview"),
        "photo_thumbnail": _job(asset, "photo_thumbnail"),
        "photo_metadata": _job(asset, "photo_metadata"),
    }
    try:
        image = _load_image_from_storage(asset.original_file_key, asset.extension)
        original_width, original_height = image.size

        exif = image.getexif()
        decoded = {}
        for key, value in exif.items():
            decoded[ExifTags.TAGS.get(key, key)] = str(value)
        MediaAssetMetadata.objects.update_or_create(media_asset=asset, defaults={"extra_metadata": decoded})
        asset.original_width = original_width
        asset.original_height = original_height
        asset.save(update_fields=["original_width", "original_height", "updated_at"])
        _complete(jobs["photo_metadata"])

        preview_key = build_preview_key(asset.owner_id, asset.collection_id, asset.id)
        asset.preview_file_key = preview_key
        asset.preview_file_size_bytes = _save_webp_variant(image, (2400, 2400), 86, preview_key)
        asset.save(update_fields=["preview_file_key", "preview_file_size_bytes", "updated_at"])
        _complete(jobs["photo_preview"])

        thumbnail_key = build_thumbnail_key(asset.owner_id, asset.collection_id, asset.id)
        asset.thumbnail_file_key = thumbnail_key
        asset.thumbnail_file_size_bytes = _save_webp_variant(image, (600, 600), 80, thumbnail_key)
        asset.save(update_fields=["thumbnail_file_key", "thumbnail_file_size_bytes", "updated_at"])
        _complete(jobs["photo_thumbnail"])

        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        for job in jobs.values():
            if job.status != "completed":
                _fail(job, exc)
        raise


@shared_task
def generate_photo_preview(media_asset_id):
    asset = MediaAsset.objects.select_related("owner", "collection").get(id=media_asset_id)
    job = _job(asset, "photo_preview")
    try:
        image = Image.open(io.BytesIO(download_bytes(asset.original_file_key)))
        image.thumbnail((2400, 2400))
        out = io.BytesIO()
        image.convert("RGB").save(out, format="WEBP", quality=86)
        body = out.getvalue()
        key = build_preview_key(asset.owner_id, asset.collection_id, asset.id)
        upload_bytes(key, body, "image/webp")
        asset.preview_file_key = key
        asset.preview_file_size_bytes = len(body)
        asset.original_width = asset.original_width or image.width
        asset.original_height = asset.original_height or image.height
        asset.save(update_fields=["preview_file_key", "preview_file_size_bytes", "original_width", "original_height", "updated_at"])
        _complete(job)
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        _fail(job, exc)
        raise


@shared_task
def generate_photo_thumbnail(media_asset_id):
    asset = MediaAsset.objects.select_related("owner", "collection").get(id=media_asset_id)
    job = _job(asset, "photo_thumbnail")
    try:
        image = Image.open(io.BytesIO(download_bytes(asset.original_file_key)))
        image.thumbnail((600, 600))
        out = io.BytesIO()
        image.convert("RGB").save(out, format="WEBP", quality=80)
        body = out.getvalue()
        key = build_thumbnail_key(asset.owner_id, asset.collection_id, asset.id)
        upload_bytes(key, body, "image/webp")
        asset.thumbnail_file_key = key
        asset.thumbnail_file_size_bytes = len(body)
        asset.save(update_fields=["thumbnail_file_key", "thumbnail_file_size_bytes", "updated_at"])
        _complete(job)
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        _fail(job, exc)
        raise


@shared_task
def extract_photo_metadata(media_asset_id):
    asset = MediaAsset.objects.get(id=media_asset_id)
    job = _job(asset, "photo_metadata")
    try:
        image = Image.open(io.BytesIO(download_bytes(asset.original_file_key)))
        asset.original_width, asset.original_height = image.size
        asset.save(update_fields=["original_width", "original_height", "updated_at"])
        exif = image.getexif()
        decoded = {}
        for key, value in exif.items():
            decoded[ExifTags.TAGS.get(key, key)] = str(value)
        MediaAssetMetadata.objects.update_or_create(media_asset=asset, defaults={"extra_metadata": decoded})
        _complete(job)
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        _fail(job, exc)
        raise


@shared_task
def extract_video_metadata(media_asset_id):
    asset = MediaAsset.objects.get(id=media_asset_id)
    job = _job(asset, "video_metadata")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / f"source.{asset.extension or 'mp4'}"
            download_to_file(asset.original_file_key, source_path)
            probe = ffmpeg.probe(str(source_path))

        video_stream = next(
            (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
            {},
        )
        duration = video_stream.get("duration") or probe.get("format", {}).get("duration")
        if duration:
            asset.duration_seconds = max(0, round(float(duration)))
        display_width, display_height = _video_display_dimensions(video_stream)
        if display_width:
            asset.original_width = display_width
        if display_height:
            asset.original_height = display_height
        asset.save(update_fields=["duration_seconds", "original_width", "original_height", "updated_at"])
        MediaAssetMetadata.objects.get_or_create(media_asset=asset)
        _complete(job)
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        _fail(job, exc)
        raise


@shared_task
def process_video_media(media_asset_id):
    asset = MediaAsset.objects.select_related("owner", "collection").get(id=media_asset_id)
    jobs = {
        "video_metadata": _job(asset, "video_metadata"),
        "video_thumbnail": _job(asset, "video_thumbnail"),
    }
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / f"source.{asset.extension or 'mp4'}"
            download_to_file(asset.original_file_key, source_path)
            probe = ffmpeg.probe(str(source_path))
            video_stream = next(
                (stream for stream in probe.get("streams", []) if stream.get("codec_type") == "video"),
                {},
            )
            duration = video_stream.get("duration") or probe.get("format", {}).get("duration")
            if duration:
                asset.duration_seconds = max(0, round(float(duration)))
            display_width, display_height = _video_display_dimensions(video_stream)
            if display_width:
                asset.original_width = display_width
            if display_height:
                asset.original_height = display_height
            asset.save(update_fields=["duration_seconds", "original_width", "original_height", "updated_at"])
            MediaAssetMetadata.objects.get_or_create(media_asset=asset)
            _complete(jobs["video_metadata"])

            body, _ = (
                ffmpeg
                .input(str(source_path), ss=0)
                .filter("scale", "min(600,iw)", -2)
                .output("pipe:", vframes=1, format="image2", vcodec="webp")
                .run(capture_stdout=True, capture_stderr=True)
            )

        thumbnail_key = build_thumbnail_key(asset.owner_id, asset.collection_id, asset.id)
        upload_bytes(thumbnail_key, body, "image/webp")
        asset.thumbnail_file_key = thumbnail_key
        asset.thumbnail_file_size_bytes = len(body)
        asset.save(update_fields=["thumbnail_file_key", "thumbnail_file_size_bytes", "updated_at"])
        _complete(jobs["video_thumbnail"])
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        for job in jobs.values():
            if job.status != "completed":
                _fail(job, exc)
        raise


@shared_task
def generate_video_thumbnail(media_asset_id):
    asset = MediaAsset.objects.get(id=media_asset_id)
    job = _job(asset, "video_thumbnail")
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / f"source.{asset.extension or 'mp4'}"
            download_to_file(asset.original_file_key, source_path)
            body, _ = (
                ffmpeg
                .input(str(source_path), ss=0)
                .filter("scale", "min(600,iw)", -2)
                .output("pipe:", vframes=1, format="image2", vcodec="webp")
                .run(capture_stdout=True, capture_stderr=True)
            )

        thumbnail_key = build_thumbnail_key(asset.owner_id, asset.collection_id, asset.id)
        upload_bytes(thumbnail_key, body, "image/webp")
        asset.thumbnail_file_key = thumbnail_key
        asset.thumbnail_file_size_bytes = len(body)
        asset.save(update_fields=["thumbnail_file_key", "thumbnail_file_size_bytes", "updated_at"])
        _complete(job)
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        _fail(job, exc)
        raise
