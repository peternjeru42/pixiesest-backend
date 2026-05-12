from django.contrib import admin

from .models import CollectionSet, SetStats


@admin.register(CollectionSet)
class CollectionSetAdmin(admin.ModelAdmin):
    list_display = ("title", "collection", "visibility", "sort_order", "deleted_at")
    list_filter = ("visibility",)
    search_fields = ("title", "collection__title", "collection__owner__email")


admin.site.register(SetStats)
