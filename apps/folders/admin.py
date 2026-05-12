from django.contrib import admin

from .models import Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "slug", "sort_order", "deleted_at", "created_at")
    search_fields = ("name", "owner__email", "slug")
    list_filter = ("show_on_homepage", "is_password_enabled")
