from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.collections.models import Collection
from apps.downloads.models import DownloadJob
from apps.favorites.models import FavoriteList

from .models import EmailLog


def _send(owner, collection, recipient_email, email_type, subject, body):
    log = EmailLog.objects.create(owner=owner, collection=collection, recipient_email=recipient_email, email_type=email_type)
    try:
        send_mail(subject, body, None, [recipient_email], fail_silently=False)
        log.status = "sent"
        log.sent_at = timezone.now()
        log.save(update_fields=["status", "sent_at"])
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        log.save(update_fields=["status", "error_message"])
        raise
    return str(log.id)


@shared_task
def send_collection_invite_email(collection_id, recipient_email, message=""):
    collection = Collection.objects.select_related("owner", "download_settings").get(id=collection_id)
    gallery_url = f"{settings.FRONTEND_URL.rstrip('/')}/galleries/{collection.slug}"
    owner_name = " ".join(part for part in [collection.owner.first_name, collection.owner.last_name] if part).strip()
    sender_name = collection.owner.business_name or owner_name or collection.owner.email
    body_parts = [
        message.strip() or f"{sender_name} shared a gallery with you.",
        "",
        collection.title,
    ]
    if collection.description:
        body_parts.extend(["", collection.description])
    body_parts.extend(["", f"View the gallery: {gallery_url}"])
    if hasattr(collection, "download_settings") and collection.download_settings.download_pin_enabled:
        body_parts.extend(["", f"Download PIN: {collection.download_settings.download_pin}"])
    return _send(
        collection.owner,
        collection,
        recipient_email,
        "collection_invite",
        f"Gallery invitation: {collection.title}",
        "\n".join(body_parts),
    )


@shared_task
def send_download_ready_email(download_job_id):
    job = DownloadJob.objects.select_related("collection", "collection__owner").get(id=download_job_id)
    return _send(job.collection.owner, job.collection, job.requested_by_email, "download_zip_ready", "Your download is ready", "Your gallery ZIP is ready to download.")


@shared_task
def send_favorite_submitted_email(favorite_list_id):
    fav = FavoriteList.objects.select_related("collection", "collection__owner").get(id=favorite_list_id)
    return _send(fav.collection.owner, fav.collection, fav.collection.owner.email, "favorite_list_submitted", "Favorite list submitted", f"{fav.client_email} submitted favorites.")
