import logging
import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.collection_sets.models import CollectionSet
from apps.collections.models import Collection
from apps.core.utils import extension_from_filename, safe_filename
from apps.media_assets.models import MediaAsset
from apps.quotas.services import check_user_has_storage_space
from apps.storage.services import build_original_key, delete_object, object_exists

from .models import MediaUploadSession

logger = logging.getLogger(__name__)


def infer_media_type(mime_type):
    if mime_type == "image/gif":
        return "gif"
    if mime_type.startswith("video/"):
        return "video"
    return "photo"


@transaction.atomic
def create_upload_session(user, *, collection_id, set_id, original_filename, mime_type, file_size_bytes):
    check_user_has_storage_space(user, file_size_bytes)
    collection = Collection.objects.get(id=collection_id, owner=user)
    set_obj = CollectionSet.objects.get(id=set_id, collection=collection) if set_id else None
    ext = extension_from_filename(original_filename)
    asset = MediaAsset.objects.create(
        owner=user,
        collection=collection,
        set=set_obj,
        media_type=infer_media_type(mime_type),
        original_filename=safe_filename(original_filename),
        display_filename=safe_filename(original_filename),
        original_file_key="pending",
        mime_type=mime_type,
        extension=ext,
        file_size_bytes=file_size_bytes,
        status="uploading",
    )
    key = build_original_key(user.id, collection.id, asset.id, ext)
    asset.original_file_key = key
    asset.save(update_fields=["original_file_key", "updated_at"])
    session = MediaUploadSession.objects.create(
        owner=user,
        collection=collection,
        set=set_obj,
        media_asset=asset,
        upload_id=uuid.uuid4().hex,
        original_filename=asset.original_filename,
        mime_type=mime_type,
        file_size_bytes=file_size_bytes,
        r2_object_key=key,
        status="pending",
        expires_at=timezone.now() + timedelta(hours=2),
    )
    return session


@transaction.atomic
def complete_upload(user, upload_id, checksum=""):
    session = MediaUploadSession.objects.select_for_update().get(upload_id=upload_id, owner=user)
    if session.status in {"processing", "completed"}:
        return session
    if session.status in {"cancelled", "expired"}:
        raise ValueError("Upload session is no longer active.")
    if not object_exists(session.r2_object_key):
        session.status = "failed"
        session.save(update_fields=["status", "updated_at"])
        raise ValueError("Uploaded object was not found in R2.")
    asset = session.media_asset
    asset.status = "processing"
    asset.uploaded_at = timezone.now()
    asset.checksum = checksum or asset.checksum
    asset.save(update_fields=["status", "uploaded_at", "checksum", "updated_at"])
    session.status = "processing"
    session.save(update_fields=["status", "updated_at"])

    transaction.on_commit(lambda: queue_media_processing(asset.id))
    return session


def find_duplicate_for_upload(user, collection_id, original_filename, file_size_bytes, checksum="", exclude_asset_id=None):
    candidates = MediaAsset.objects.filter(
        owner=user,
        collection_id=collection_id,
        file_size_bytes=file_size_bytes,
    ).exclude(status__in={"uploading", "deleted"})
    if exclude_asset_id:
        candidates = candidates.exclude(id=exclude_asset_id)

    filename_match = Q(original_filename__iexact=original_filename)
    if checksum:
        candidates = candidates.filter(Q(checksum=checksum) | (Q(checksum="") & filename_match))
    else:
        candidates = candidates.filter(filename_match)
    return candidates.order_by("-created_at").first()


def find_duplicate_asset(asset):
    return find_duplicate_for_upload(
        asset.owner,
        asset.collection_id,
        asset.original_filename,
        asset.file_size_bytes,
        asset.checksum,
        exclude_asset_id=asset.id,
    )


@transaction.atomic
def cancel_upload(user, upload_id):
    session = MediaUploadSession.objects.select_for_update().get(upload_id=upload_id, owner=user)
    asset = session.media_asset
    if session.status in {"processing", "completed"} or (asset and asset.status != "uploading"):
        return session

    session.status = "cancelled"
    session.save(update_fields=["status", "updated_at"])
    if asset and asset.status == "uploading":
        asset.delete()
    transaction.on_commit(lambda: delete_upload_object(session.r2_object_key, session.upload_id))
    return session


def delete_upload_object(object_key, upload_id):
    try:
        delete_object(object_key)
    except Exception:
        logger.exception("Unable to delete abandoned upload object.", extra={"upload_id": upload_id})


def queue_media_processing(asset_id):
    from apps.media_processing.tasks import process_uploaded_media
    from apps.notifications.tasks import send_upload_summary_email

    try:
        process_uploaded_media.delay(str(asset_id))
    except Exception:
        logger.exception("Unable to enqueue media processing.", extra={"media_asset_id": str(asset_id)})
        MediaAsset.objects.filter(id=asset_id).update(status="failed", updated_at=timezone.now())
        session = MediaUploadSession.objects.filter(media_asset_id=asset_id).first()
        if session:
            session.status = "failed"
            session.save(update_fields=["status", "updated_at"])
            try:
                send_upload_summary_email.apply_async(args=[str(session.id)], countdown=120)
            except Exception:
                logger.exception("Unable to queue failed upload summary.", extra={"upload_session_id": str(session.id)})
