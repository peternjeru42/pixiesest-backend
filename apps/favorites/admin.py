from django.contrib import admin

from .models import FavoriteItem, FavoriteList, FavoriteListActivity


@admin.register(FavoriteList)
class FavoriteListAdmin(admin.ModelAdmin):
    list_display = ("name", "collection", "client_email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("client_email", "client_name", "collection__title")


admin.site.register(FavoriteItem)
admin.site.register(FavoriteListActivity)
