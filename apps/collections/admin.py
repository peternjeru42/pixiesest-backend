from django.contrib import admin

from .models import Collection, CollectionDesignSettings, CollectionDownloadSettings, CollectionPrivacySettings


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "status", "visibility", "sort_order", "deleted_at", "created_at")
    list_filter = ("status", "visibility")
    search_fields = ("title", "owner__email", "slug")


admin.site.register(CollectionPrivacySettings)
admin.site.register(CollectionDownloadSettings)
admin.site.register(CollectionDesignSettings)
