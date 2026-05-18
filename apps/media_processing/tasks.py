import io
import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from PIL import Image, ExifTags

from apps.media_assets.models import MediaAsset, MediaAssetMetadata
from apps.profiles.services import recalculate_user_profile_stats
from apps.quotas.services import increase_storage_usage
from apps.storage.services import build_preview_key, build_thumbnail_key, download_bytes, upload_bytes

from .models import MediaProcessingJob

logger = logging.getLogger(__name__)


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
        increase_storage_usage(asset.owner, asset.file_size_bytes, "original_upload", media_asset=asset)
        recalculate_user_profile_stats(asset.owner)


@shared_task
def process_uploaded_media(media_asset_id):
    asset = MediaAsset.objects.select_related("owner", "collection", "set").get(id=media_asset_id)
    try:
        asset.status = "processing"
        asset.processed_at = None
        asset.save(update_fields=["status", "processed_at", "updated_at"])
        MediaProcessingJob.objects.filter(media_asset=asset, job_type__in=_required_job_types(asset)).delete()
        if asset.media_type in {"photo", "gif"}:
            generate_photo_preview.delay(str(asset.id))
            generate_photo_thumbnail.delay(str(asset.id))
            extract_photo_metadata.delay(str(asset.id))
        else:
            extract_video_metadata.delay(str(asset.id))
            generate_video_thumbnail.delay(str(asset.id))
        return str(asset.id)
    except Exception:
        logger.exception("Media processing failed.", extra={"media_asset_id": str(asset.id)})
        _mark_asset_processing_failed(asset.id)
        raise


def _update_upload_session(asset, status):
    from apps.media_uploads.models import MediaUploadSession

    MediaUploadSession.objects.filter(media_asset=asset).update(status=status, updated_at=timezone.now())


@shared_task
def generate_photo_preview(media_asset_id):
    asset = MediaAsset.objects.select_related("owner", "collection").get(id=media_asset_id)
    job = _job(asset, "photo_preview")
    try:
        image = Image.open(io.BytesIO(download_bytes(asset.original_file_key)))
        image.thumbnail((2400, 2400))
        out = io.BytesIO()
        image.convert("RGB").save(out, format="WEBP", quality=86)
        key = build_preview_key(asset.owner_id, asset.collection_id, asset.id)
        upload_bytes(key, out.getvalue(), "image/webp")
        asset.preview_file_key = key
        asset.original_width = asset.original_width or image.width
        asset.original_height = asset.original_height or image.height
        asset.save(update_fields=["preview_file_key", "original_width", "original_height", "updated_at"])
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
        key = build_thumbnail_key(asset.owner_id, asset.collection_id, asset.id)
        upload_bytes(key, out.getvalue(), "image/webp")
        asset.thumbnail_file_key = key
        asset.save(update_fields=["thumbnail_file_key", "updated_at"])
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
        MediaAssetMetadata.objects.get_or_create(media_asset=asset)
        _complete(job)
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        _fail(job, exc)
        raise


@shared_task
def generate_video_thumbnail(media_asset_id):
    asset = MediaAsset.objects.get(id=media_asset_id)
    job = _job(asset, "video_thumbnail")
    try:
        # Placeholder: production workers should call ffmpeg to create a still frame.
        asset.thumbnail_file_key = asset.thumbnail_file_key
        asset.save(update_fields=["thumbnail_file_key", "updated_at"])
        _complete(job)
        _finish_asset_if_processing_complete(asset.id)
    except Exception as exc:
        _fail(job, exc)
        raise
