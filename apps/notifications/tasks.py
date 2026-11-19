from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.billing.models import PaymentTransaction, Subscription
from apps.downloads.models import DownloadJob
from apps.favorites.models import FavoriteList
from apps.media_uploads.models import MediaUploadSession

from .emails import send_branded_email
from .models import EmailLog


def _gallery_url(collection):
    return f"{settings.FRONTEND_URL.rstrip('/')}/galleries/{collection.slug}"


def _dashboard_url(path=""):
    suffix = f"/{path.lstrip('/')}" if path else ""
    return f"{settings.FRONTEND_URL.rstrip('/')}/dashboard{suffix}"


def _owner_name(owner):
    full_name = " ".join(part for part in [owner.first_name, owner.last_name] if part).strip()
    return owner.business_name or full_name or owner.email


def _get_or_create_log(*, dedupe_key, **kwargs):
    return EmailLog.objects.get_or_create(dedupe_key=dedupe_key, defaults=kwargs)


def _send(log, **email):
    try:
        send_branded_email(recipient=log.recipient_email, **email)
        log.status = "sent"
        log.sent_at = timezone.now()
        log.error_message = ""
        log.save(update_fields=["status", "sent_at", "error_message"])
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)[:4000]
        log.save(update_fields=["status", "error_message"])
        raise
    return str(log.id)


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_welcome_email(user_id):
    user = get_user_model().objects.get(id=user_id)
    log, created = _get_or_create_log(
        dedupe_key=f"welcome-free-plan:{user.id}",
        owner=user,
        recipient_email=user.email,
        email_type="welcome_free_plan",
    )
    if not created and log.status != "failed":
        return str(log.id)
    first_name = (user.first_name or "").strip()
    greeting = f"Welcome, {first_name}." if first_name else "Welcome to Droptop."
    return _send(
        log,
        subject="Welcome to Droptop — your free 5 GB is ready",
        preheader="Your Free plan includes 5 GB of storage for photos and videos.",
        eyebrow="Your Droptop account",
        heading=greeting,
        paragraphs=[
            "Your account starts on the Free plan with 5 GB of storage available for your photos and videos.",
            "Create your first gallery whenever you are ready. No payment is required to use your free allocation.",
        ],
        cta_label="Create your first gallery",
        cta_url=f"{settings.FRONTEND_URL.rstrip('/')}/collections/new",
        metrics=[("Storage included", "5 GB"), ("Plan", "Free")],
        note="You can review your storage usage and upgrade options at any time from your Droptop dashboard.",
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_collection_invite_email(email_log_id, message=""):
    log = EmailLog.objects.select_related("owner", "collection", "collection__owner").get(id=email_log_id)
    collection = log.collection
    if not collection:
        log.status = "failed"
        log.error_message = "The collection no longer exists."
        log.save(update_fields=["status", "error_message"])
        return str(log.id)
    sender_name = _owner_name(collection.owner)
    return _send(
        log,
        subject=f"{sender_name} shared {collection.title} with you",
        preheader=f"Your gallery, {collection.title}, is ready to view.",
        eyebrow="Gallery invitation",
        heading=collection.title,
        paragraphs=[
            message.strip() or f"{sender_name} shared a new gallery with you.",
            collection.description,
        ],
        cta_label="View gallery",
        cta_url=_gallery_url(collection),
        details=[("Shared by", sender_name)],
        note="If the gallery is protected, use the access details the sender shared with you separately.",
        reply_to=collection.owner.email,
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_collection_update_email(email_log_id, message=""):
    log = EmailLog.objects.select_related("collection", "collection__owner").get(id=email_log_id)
    collection = log.collection
    if not collection:
        return str(log.id)
    sender_name = _owner_name(collection.owner)
    return _send(
        log,
        subject=f"New photos or videos were added to {collection.title}",
        preheader=f"There is something new to see in {collection.title}.",
        eyebrow="Gallery updated",
        heading="There’s more to see.",
        paragraphs=[
            message.strip() or f"{sender_name} added new photos or videos to {collection.title}.",
            "The same gallery link now includes the latest additions.",
        ],
        cta_label="See what’s new",
        cta_url=_gallery_url(collection),
        details=[("Gallery", collection.title), ("Updated by", sender_name)],
        note="Your existing gallery access still applies.",
        reply_to=collection.owner.email,
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_download_ready_email(download_job_id):
    job = DownloadJob.objects.select_related("collection", "collection__owner").get(id=download_job_id)
    if not getattr(job, "requested_by_email", ""):
        return ""
    log, created = _get_or_create_log(
        dedupe_key=f"download-ready:{job.id}",
        owner=job.collection.owner,
        collection=job.collection,
        recipient_email=job.requested_by_email,
        email_type="download_zip_ready",
    )
    if not created and log.status != "failed":
        return str(log.id)
    return _send(
        log,
        subject=f"Your {job.collection.title} download is ready",
        preheader="Your gallery files have been prepared.",
        eyebrow="Download ready",
        heading="Your files are ready.",
        paragraphs=["We finished preparing your gallery download.", "Open the gallery to download the ZIP file."],
        cta_label="Open gallery",
        cta_url=_gallery_url(job.collection),
        details=[("Gallery", job.collection.title), ("Quality", job.download_quality.replace("_", " ").title())],
        note="For your privacy, the download link is available from the gallery and follows the gallery’s access settings.",
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_client_download_email(download_job_id):
    job = DownloadJob.objects.select_related("collection", "collection__owner").get(id=download_job_id)
    if not getattr(job, "requested_by_email", ""):
        return ""
    log, created = _get_or_create_log(
        dedupe_key=f"client-download:{job.id}",
        owner=job.collection.owner,
        collection=job.collection,
        recipient_email=job.collection.owner.email,
        email_type="client_download_completed",
    )
    if not created and log.status != "failed":
        return str(log.id)
    return _send(
        log,
        subject=f"A client prepared a download from {job.collection.title}",
        preheader="New client activity on your Droptop gallery.",
        eyebrow="Client activity",
        heading="Your gallery was downloaded.",
        paragraphs=[f"{job.requested_by_email} prepared a ZIP download from {job.collection.title}."],
        cta_label="View collection",
        cta_url=f"{settings.FRONTEND_URL.rstrip('/')}/collections/{job.collection_id}",
        details=[("Client", job.requested_by_email), ("Quality", job.download_quality.replace("_", " ").title())],
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_favorite_submitted_email(favorite_list_id):
    fav = FavoriteList.objects.select_related("collection", "collection__owner").prefetch_related("items").get(id=favorite_list_id)
    log, created = _get_or_create_log(
        dedupe_key=f"favorite-submitted:{fav.id}",
        owner=fav.collection.owner,
        collection=fav.collection,
        recipient_email=fav.collection.owner.email,
        email_type="favorite_list_submitted",
    )
    if not created and log.status != "failed":
        return str(log.id)
    count = fav.items.count()
    return _send(
        log,
        subject=f"New favorites submitted for {fav.collection.title}",
        preheader=f"{fav.client_email} submitted {count} favorite files.",
        eyebrow="Client activity",
        heading="A favorite list is ready.",
        paragraphs=[f"{fav.client_email} finished selecting favorites from {fav.collection.title}."],
        cta_label="Review favorites",
        cta_url=f"{settings.FRONTEND_URL.rstrip('/')}/collections/{fav.collection_id}/favorites",
        metrics=[("Selected", count)],
        details=[("Client", fav.client_email), ("Gallery", fav.collection.title)],
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_upload_summary_email(anchor_session_id):
    anchor = MediaUploadSession.objects.select_related("owner", "collection").get(id=anchor_session_id)
    lower_bound = anchor.created_at - timedelta(minutes=30)
    now = timezone.now()
    with transaction.atomic():
        sessions = list(
            MediaUploadSession.objects.select_for_update()
            .filter(
                owner=anchor.owner,
                collection=anchor.collection,
                status__in=["completed", "failed"],
                notification_sent_at__isnull=True,
                created_at__gte=lower_bound,
            )
            .order_by("created_at")
        )
        if not sessions:
            return ""
        MediaUploadSession.objects.filter(id__in=[session.id for session in sessions]).update(notification_sent_at=now)

    completed = [session for session in sessions if session.status == "completed"]
    failed = [session for session in sessions if session.status == "failed"]
    log, created = _get_or_create_log(
        dedupe_key=f"upload-summary:{sessions[0].id}:{sessions[-1].id}",
        owner=anchor.owner,
        collection=anchor.collection,
        recipient_email=anchor.owner.email,
        email_type="upload_summary",
    )
    if not created and log.status != "failed":
        return str(log.id)

    heading = "Your upload is complete." if not failed else "Your upload needs attention."
    paragraphs = [f"We finished processing the latest files added to {anchor.collection.title}."]
    if failed:
        preview = ", ".join(session.original_filename for session in failed[:3])
        remainder = len(failed) - 3
        paragraphs.append(f"Files that could not be processed: {preview}{f' and {remainder} more' if remainder > 0 else ''}.")
    try:
        return _send(
            log,
            subject=f"Upload summary for {anchor.collection.title}",
            preheader=f"{len(completed)} uploaded, {len(failed)} need attention.",
            eyebrow="Upload summary",
            heading=heading,
            paragraphs=paragraphs,
            cta_label="Review collection",
            cta_url=f"{settings.FRONTEND_URL.rstrip('/')}/collections/{anchor.collection_id}/media",
            metrics=[("Uploaded", len(completed)), ("Needs attention", len(failed))],
            note="Failed files remain visible in your upload activity so you can retry them; they are not silently discarded.",
        )
    except Exception:
        MediaUploadSession.objects.filter(id__in=[session.id for session in sessions]).update(notification_sent_at=None)
        raise


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_payment_success_email(payment_id):
    payment = PaymentTransaction.objects.select_related("user", "plan").get(id=payment_id)
    log, created = _get_or_create_log(
        dedupe_key=f"billing-receipt:{payment.reference}",
        owner=payment.user,
        recipient_email=payment.user.email,
        email_type="billing_receipt",
    )
    if not created and log.status != "failed":
        return str(log.id)
    amount = f"{payment.currency.upper()} {payment.expected_amount_minor / 100:,.2f}"
    return _send(
        log,
        subject=f"Payment confirmed for Droptop {payment.plan.name}",
        preheader=f"Your {payment.plan.name} plan is active.",
        eyebrow="Payment confirmed",
        heading="You’re all set.",
        paragraphs=[f"We received your payment and activated Droptop {payment.plan.name}."],
        cta_label="View billing",
        cta_url=_dashboard_url("billing"),
        details=[("Plan", payment.plan.name), ("Amount", amount), ("Reference", payment.reference)],
        note="Keep this email as your payment confirmation.",
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_payment_failed_email(subscription_id, event_id):
    subscription = Subscription.objects.select_related("user", "plan").get(id=subscription_id)
    log, created = _get_or_create_log(
        dedupe_key=f"payment-failed:{event_id}",
        owner=subscription.user,
        recipient_email=subscription.user.email,
        email_type="payment_failed",
    )
    if not created and log.status != "failed":
        return str(log.id)
    grace_end = subscription.grace_period_ends_at
    return _send(
        log,
        subject="Action needed: your Droptop payment failed",
        preheader="Update your payment method to keep your plan active.",
        eyebrow="Payment issue",
        heading="We couldn’t process your payment.",
        paragraphs=[
            f"Your payment for Droptop {subscription.plan.name} did not go through.",
            "Update your payment method to prevent an interruption to your storage and galleries.",
        ],
        cta_label="Update payment method",
        cta_url=_dashboard_url("billing"),
        details=[
            ("Plan", subscription.plan.name),
            ("Grace period ends", grace_end.strftime("%d %b %Y") if grace_end else "Soon"),
        ],
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_storage_warning_email(quota_id, threshold, cycle):
    from apps.quotas.models import StorageQuota

    quota = StorageQuota.objects.select_related("user").get(id=quota_id)
    log, created = _get_or_create_log(
        dedupe_key=f"storage-warning:{quota.id}:{cycle}:{threshold}",
        owner=quota.user,
        recipient_email=quota.user.email,
        email_type="storage_warning",
    )
    if not created and log.status != "failed":
        return str(log.id)
    used_gb = quota.storage_used_bytes / 1024**3
    limit_gb = quota.storage_limit_bytes / 1024**3
    is_full = threshold >= 100
    return _send(
        log,
        subject="Your Droptop storage is full" if is_full else f"Your Droptop storage is {threshold}% full",
        preheader="Review your storage before your next upload.",
        eyebrow="Storage alert",
        heading="Your storage is full." if is_full else "You’re running low on storage.",
        paragraphs=[
            "New uploads may not complete until space is available." if is_full else "You still have room, but it is a good time to review your files or plan.",
        ],
        cta_label="Manage storage",
        cta_url=_dashboard_url("storage"),
        metrics=[("Used", f"{used_gb:,.1f} GB"), ("Limit", f"{limit_gb:,.0f} GB")],
        note="Droptop only sends another storage alert when you cross a higher threshold, or after usage drops below 70% and rises again.",
    )
