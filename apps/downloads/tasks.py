import io
import zipfile

from celery import shared_task
from django.utils import timezone

from apps.storage.services import build_export_key, download_bytes, upload_bytes

from .models import DownloadJob
from .services import get_downloadable_assets_for_job


def _generate_zip(download_job_id, quality="original"):
    job = DownloadJob.objects.select_related("collection", "collection__owner", "favorite_list").get(id=download_job_id)
    job.status = "running"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])
    try:
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for asset in get_downloadable_assets_for_job(job):
                key = asset.original_file_key if quality == "original" else asset.preview_file_key
                # Originals are copied byte-for-byte from R2 into the ZIP without recompression or resizing.
                zf.writestr(asset.original_filename, download_bytes(key))
        body = archive.getvalue()
        key = build_export_key(job.collection.owner_id, job.collection_id, job.id)
        upload_bytes(key, body, "application/zip")
        job.zip_file_key = key
        job.file_size_bytes = len(body)
        job.status = "completed"
        job.completed_at = timezone.now()
        job.save(update_fields=["zip_file_key", "file_size_bytes", "status", "completed_at", "updated_at"])
    except Exception:
        job.status = "failed"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at", "updated_at"])
        raise
    return str(job.id)


@shared_task
def generate_collection_original_zip(download_job_id):
    return _generate_zip(download_job_id, quality="original")


@shared_task
def generate_collection_web_size_zip(download_job_id):
    return _generate_zip(download_job_id, quality="web_size")


@shared_task
def generate_favorites_original_zip(download_job_id):
    return _generate_zip(download_job_id, quality="original")


@shared_task
def generate_favorites_web_size_zip(download_job_id):
    return _generate_zip(download_job_id, quality="web_size")


@shared_task
def cleanup_expired_download_exports():
    DownloadJob.objects.filter(expires_at__lt=timezone.now(), status="completed").update(status="expired")
