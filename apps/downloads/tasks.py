import logging
import tempfile
import zipfile
from pathlib import Path

from celery import shared_task
from django.utils import timezone

from apps.storage.services import build_export_key, delete_object, download_to_file, upload_file

from .models import DownloadJob
from .services import get_downloadable_assets_for_job

logger = logging.getLogger(__name__)


def _generate_zip(download_job_id, quality="original"):
    job = DownloadJob.objects.select_related("collection", "collection__owner", "favorite_list").get(id=download_job_id)
    job.status = "running"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at", "updated_at"])
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            archive_path = temp_dir_path / "gallery.zip"
            source_path = temp_dir_path / "source"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
                for asset in get_downloadable_assets_for_job(job).iterator(chunk_size=100):
                    object_key = asset.original_file_key if quality == "original" else asset.preview_file_key
                    download_to_file(object_key, source_path)
                    zf.write(source_path, arcname=asset.original_filename)
                    source_path.unlink(missing_ok=True)

            key = build_export_key(job.collection.owner_id, job.collection_id, job.id)
            file_size_bytes = archive_path.stat().st_size
            upload_file(key, archive_path, "application/zip")

        job.zip_file_key = key
        job.file_size_bytes = file_size_bytes
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
    DownloadJob.objects.filter(
        expires_at__lt=timezone.now(),
        status="completed",
        zip_file_key="",
    ).update(status="expired")
    expired_jobs = DownloadJob.objects.filter(
        expires_at__lt=timezone.now(),
        status="completed",
    ).exclude(zip_file_key="")
    cleaned = 0
    for job in expired_jobs.iterator(chunk_size=100):
        try:
            delete_object(job.zip_file_key)
        except Exception:
            logger.exception("Unable to delete expired download export.", extra={"download_job_id": str(job.id)})
            continue
        job.status = "expired"
        job.zip_file_key = ""
        job.save(update_fields=["status", "zip_file_key", "updated_at"])
        cleaned += 1
    return cleaned
