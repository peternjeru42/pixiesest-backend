from django.contrib import admin

from .models import MediaProcessingJob


@admin.register(MediaProcessingJob)
class MediaProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("media_asset", "job_type", "status", "attempts", "created_at")
    list_filter = ("job_type", "status")
    search_fields = ("media_asset__display_filename", "media_asset__owner__email")
