from django.contrib import admin

from .models import StorageQuota, StorageUsageLog


@admin.register(StorageQuota)
class StorageQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "plan_name", "storage_used_bytes", "storage_limit_bytes", "is_active")
    search_fields = ("user__email", "plan_name")


@admin.register(StorageUsageLog)
class StorageUsageLogAdmin(admin.ModelAdmin):
    list_display = ("user", "change_type", "bytes_changed", "reason", "created_at")
    search_fields = ("user__email", "reason")
