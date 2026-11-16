import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from apps.storage.services import delete_object

from .models import MediaUploadSession

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_uploads():
    expired_ids = list(
        MediaUploadSession.objects.filter(
            expires_at__lt=timezone.now(),
            status__in={"pending", "uploading", "uploaded", "failed", "cancelled"},
            media_asset__status="uploading",
        ).values_list("id", flat=True)
    )
    cleaned = 0
    for session_id in expired_ids:
        with transaction.atomic():
            session = (
                MediaUploadSession.objects.select_for_update()
                .select_related("media_asset")
                .filter(
                    id=session_id,
                    status__in={"pending", "uploading", "uploaded", "failed", "cancelled"},
                    media_asset__status="uploading",
                )
                .first()
            )
            if not session:
                continue
            try:
                delete_object(session.r2_object_key)
            except Exception:
                logger.exception("Unable to delete expired upload object.", extra={"upload_id": session.upload_id})
                continue

            session.status = "expired"
            session.save(update_fields=["status", "updated_at"])
            if session.media_asset and session.media_asset.status == "uploading":
                session.media_asset.delete()
            cleaned += 1
    return cleaned
