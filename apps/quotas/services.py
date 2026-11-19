from django.db import transaction

from apps.core.exceptions import QuotaExceeded
from apps.media_assets.storage import storage_totals_for_user

from .models import StorageQuota, StorageUsageLog


def _storage_warning_threshold(quota):
    if not quota.storage_limit_bytes:
        return 0
    percentage = quota.storage_used_bytes * 100 / quota.storage_limit_bytes
    if percentage >= 100:
        return 100
    if percentage >= 95:
        return 95
    if percentage >= 80:
        return 80
    return 0


def _schedule_storage_warning(quota):
    threshold = _storage_warning_threshold(quota)
    if threshold == 0:
        if quota.storage_warning_level and quota.storage_limit_bytes and quota.storage_used_bytes * 100 / quota.storage_limit_bytes < 70:
            quota.storage_warning_level = 0
            quota.storage_warning_cycle += 1
        return
    if threshold <= quota.storage_warning_level:
        return
    quota.storage_warning_level = threshold
    from apps.notifications.tasks import send_storage_warning_email

    transaction.on_commit(
        lambda: send_storage_warning_email.delay(str(quota.id), threshold, quota.storage_warning_cycle),
        robust=True,
    )


def check_user_has_storage_space(user, bytes_needed):
    quota = StorageQuota.objects.get_or_create(user=user)[0]
    if not quota.is_active:
        raise QuotaExceeded("Storage quota is inactive.")
    current_storage_bytes = storage_totals_for_user(user)["total"]
    if current_storage_bytes + int(bytes_needed) > quota.storage_limit_bytes:
        raise QuotaExceeded("Not enough storage space for this upload.")
    return True


@transaction.atomic
def increase_storage_usage(user, bytes_changed, reason, media_asset=None):
    quota = StorageQuota.objects.select_for_update().get_or_create(user=user)[0]
    quota.storage_used_bytes += int(bytes_changed)
    _schedule_storage_warning(quota)
    quota.save(update_fields=["storage_used_bytes", "storage_warning_level", "storage_warning_cycle", "updated_at"])
    StorageUsageLog.objects.create(
        user=user, media_asset=media_asset, change_type="increase", bytes_changed=bytes_changed, reason=reason
    )
    return quota


@transaction.atomic
def decrease_storage_usage(user, bytes_changed, reason, media_asset=None):
    quota = StorageQuota.objects.select_for_update().get_or_create(user=user)[0]
    quota.storage_used_bytes = max(0, quota.storage_used_bytes - int(bytes_changed))
    _schedule_storage_warning(quota)
    quota.save(update_fields=["storage_used_bytes", "storage_warning_level", "storage_warning_cycle", "updated_at"])
    StorageUsageLog.objects.create(
        user=user, media_asset=media_asset, change_type="decrease", bytes_changed=-abs(int(bytes_changed)), reason=reason
    )
    return quota


@transaction.atomic
def recalculate_storage_usage(user, refresh_missing=False):
    total = storage_totals_for_user(user, refresh_missing=refresh_missing)["total"]
    quota = StorageQuota.objects.select_for_update().get_or_create(user=user)[0]
    delta = total - quota.storage_used_bytes
    quota.storage_used_bytes = total
    _schedule_storage_warning(quota)
    quota.save(update_fields=["storage_used_bytes", "storage_warning_level", "storage_warning_cycle", "updated_at"])
    StorageUsageLog.objects.create(user=user, change_type="recalculate", bytes_changed=delta, reason="manual_recalculate")
    return quota
