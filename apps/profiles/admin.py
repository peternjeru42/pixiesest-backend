from django.contrib import admin

from .models import UserProfile, UserProfileStats


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "business_name", "updated_at")
    search_fields = ("user__email", "display_name", "business_name")


@admin.register(UserProfileStats)
class UserProfileStatsAdmin(admin.ModelAdmin):
    list_display = ("user", "total_photos", "total_videos", "total_storage_bytes", "updated_at")
    search_fields = ("user__email",)
