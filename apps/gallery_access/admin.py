from django.contrib import admin

from .models import AccessAttempt, GallerySession


@admin.register(GallerySession)
class GallerySessionAdmin(admin.ModelAdmin):
    list_display = ("collection", "folder", "client_email", "access_type", "expires_at", "created_at")
    list_filter = ("access_type",)
    search_fields = ("client_email", "collection__title", "folder__name")


@admin.register(AccessAttempt)
class AccessAttemptAdmin(admin.ModelAdmin):
    list_display = ("collection", "folder", "email", "attempt_type", "success", "created_at")
    list_filter = ("attempt_type", "success")
    search_fields = ("email", "collection__title", "folder__name")
