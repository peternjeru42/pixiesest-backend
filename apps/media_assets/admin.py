from django.contrib import admin

from .models import MediaAsset, MediaAssetMetadata


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("display_filename", "owner", "collection", "media_type", "status", "file_size_bytes", "created_at")
    list_filter = ("media_type", "status", "is_private", "is_downloadable")
    search_fields = ("display_filename", "original_filename", "owner__email")


admin.site.register(MediaAssetMetadata)
