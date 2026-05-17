import hashlib
from datetime import timedelta

from django.contrib.auth.hashers import check_password
from django.core import signing
from django.utils import timezone

from apps.core.exceptions import GalleryAccessDenied

from .models import AccessAttempt, GallerySession

SALT = "gallery-session"


def _request_meta(request):
    return {
        "ip_address": request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0] or None,
        "user_agent": request.META.get("HTTP_USER_AGENT", ""),
    }


def hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_gallery_session(request, *, collection=None, folder=None, client_email="", client_name="", access_type="guest"):
    expires_at = timezone.now() + timedelta(days=7)
    payload = {
        "collection_id": str(collection.id) if collection else "",
        "folder_id": str(folder.id) if folder else "",
        "client_email": client_email,
        "access_type": access_type,
        "exp": int(expires_at.timestamp()),
    }
    token = signing.dumps(payload, salt=SALT)
    GallerySession.objects.create(
        collection=collection,
        folder=folder,
        client_email=client_email,
        client_name=client_name,
        access_type=access_type,
        session_token_hash=hash_token(token),
        expires_at=expires_at,
        last_seen_at=timezone.now(),
        **_request_meta(request),
    )
    return token


def get_gallery_session(request):
    token = request.headers.get("X-Gallery-Session") or request.COOKIES.get("gallery_session")
    if not token:
        return None
    try:
        signing.loads(token, salt=SALT)
    except signing.BadSignature:
        return None
    session = GallerySession.objects.filter(session_token_hash=hash_token(token), expires_at__gt=timezone.now()).first()
    if session:
        session.last_seen_at = timezone.now()
        session.save(update_fields=["last_seen_at"])
    return session


def verify_collection_password(request, collection, password, email=""):
    ok = collection.privacy_settings.is_password_enabled and check_password(password, collection.privacy_settings.password_hash)
    AccessAttempt.objects.create(collection=collection, email=email, attempt_type="collection_password", success=ok, **_request_meta(request))
    if not ok:
        raise GalleryAccessDenied("Invalid collection password.")
    return create_gallery_session(request, collection=collection, client_email=email, access_type="guest")


def verify_folder_password(request, folder, password, email=""):
    ok = folder.is_password_enabled and check_password(password, folder.password_hash)
    AccessAttempt.objects.create(folder=folder, email=email, attempt_type="folder_password", success=ok, **_request_meta(request))
    if not ok:
        raise GalleryAccessDenied("Invalid folder password.")
    return create_gallery_session(request, folder=folder, client_email=email, access_type="guest")


def verify_client_password(request, collection, password, email, client_name=""):
    ok = collection.privacy_settings.is_client_access_enabled and check_password(password, collection.privacy_settings.client_password_hash)
    AccessAttempt.objects.create(collection=collection, email=email, attempt_type="client_password", success=ok, **_request_meta(request))
    if not ok:
        raise GalleryAccessDenied("Invalid client password.")
    return create_gallery_session(request, collection=collection, client_email=email, client_name=client_name, access_type="client")


def has_collection_access(request, collection, require_client=False):
    if collection.status != "published":
        raise GalleryAccessDenied("Collection is not published.")
    if collection.visibility == "public" and not require_client:
        return True
    session = get_gallery_session(request)
    if not session:
        raise GalleryAccessDenied()
    if session.collection_id == collection.id or (collection.folder_id and session.folder_id == collection.folder_id):
        if require_client and session.access_type != "client":
            raise GalleryAccessDenied("Client-level access required.")
        return True
    raise GalleryAccessDenied()


def has_folder_access(request, folder):
    if not folder.is_password_enabled:
        return True
    session = get_gallery_session(request)
    if session and session.folder_id == folder.id:
        return True
    raise GalleryAccessDenied()
