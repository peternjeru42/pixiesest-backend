from django.contrib import admin

from .models import ActivityEvent


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("owner", "event_type", "actor_type", "actor_email", "created_at")
    list_filter = ("event_type", "actor_type")
    search_fields = ("owner__email", "actor_email", "event_type")
