import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.collection_sets.models import CollectionSet
from apps.collections.models import Collection
from apps.core.utils import extension_from_filename, safe_filename
from apps.media_assets.models import MediaAsset
from apps.quotas.services import check_user_has_storage_space
from apps.storage.services import build_original_key, generate_presigned_upload_url, object_exists

from .models import MediaUploadSession


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
    return session, generate_presigned_upload_url(key, mime_type)


@transaction.atomic
def complete_upload(user, upload_id, checksum=""):
    session = MediaUploadSession.objects.select_for_update().get(upload_id=upload_id, owner=user)
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
    from apps.media_processing.tasks import process_uploaded_media

    process_uploaded_media.delay(str(asset.id))
    return session
