from django.contrib import admin

from .models import DownloadJob, DownloadLog


@admin.register(DownloadJob)
class DownloadJobAdmin(admin.ModelAdmin):
    list_display = ("collection", "download_type", "download_quality", "status", "requested_by_email", "created_at")
    list_filter = ("download_type", "download_quality", "status")
    search_fields = ("collection__title", "requested_by_email")


@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ("collection", "media_asset", "client_email", "download_type", "download_quality", "created_at")
    list_filter = ("download_type", "download_quality")
    search_fields = ("collection__title", "client_email", "file_key_served")
