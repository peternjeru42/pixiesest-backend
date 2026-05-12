from django.db import transaction
from django.db.models import Sum

from apps.core.exceptions import QuotaExceeded

from .models import StorageQuota, StorageUsageLog


def check_user_has_storage_space(user, bytes_needed):
    quota = StorageQuota.objects.get_or_create(user=user)[0]
    if not quota.is_active:
        raise QuotaExceeded("Storage quota is inactive.")
    if quota.storage_used_bytes + int(bytes_needed) > quota.storage_limit_bytes:
        raise QuotaExceeded("Not enough storage space for this upload.")
    return True


@transaction.atomic
def increase_storage_usage(user, bytes_changed, reason, media_asset=None):
    quota = StorageQuota.objects.select_for_update().get_or_create(user=user)[0]
    quota.storage_used_bytes += int(bytes_changed)
    quota.save(update_fields=["storage_used_bytes", "updated_at"])
    StorageUsageLog.objects.create(
        user=user, media_asset=media_asset, change_type="increase", bytes_changed=bytes_changed, reason=reason
    )
    return quota


@transaction.atomic
def decrease_storage_usage(user, bytes_changed, reason, media_asset=None):
    quota = StorageQuota.objects.select_for_update().get_or_create(user=user)[0]
    quota.storage_used_bytes = max(0, quota.storage_used_bytes - int(bytes_changed))
    quota.save(update_fields=["storage_used_bytes", "updated_at"])
    StorageUsageLog.objects.create(
        user=user, media_asset=media_asset, change_type="decrease", bytes_changed=-abs(int(bytes_changed)), reason=reason
    )
    return quota


@transaction.atomic
def recalculate_storage_usage(user):
    from apps.media_assets.models import MediaAsset

    total = (
        MediaAsset.objects.filter(owner=user)
        .exclude(status="deleted")
        .aggregate(total=Sum("file_size_bytes"))
        .get("total")
        or 0
    )
    quota = StorageQuota.objects.select_for_update().get_or_create(user=user)[0]
    delta = total - quota.storage_used_bytes
    quota.storage_used_bytes = total
    quota.save(update_fields=["storage_used_bytes", "updated_at"])
    StorageUsageLog.objects.create(user=user, change_type="recalculate", bytes_changed=delta, reason="manual_recalculate")
    return quota
