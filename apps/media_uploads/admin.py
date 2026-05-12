from django.contrib import admin

from .models import MediaUploadSession


@admin.register(MediaUploadSession)
class MediaUploadSessionAdmin(admin.ModelAdmin):
    list_display = ("upload_id", "owner", "status", "original_filename", "file_size_bytes", "expires_at")
    list_filter = ("status",)
    search_fields = ("upload_id", "owner__email", "original_filename")
