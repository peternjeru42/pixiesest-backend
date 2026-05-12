from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "business_name", "is_active", "is_staff", "created_at")
    search_fields = ("email", "business_name", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("first_name", "last_name", "business_name", "phone_number", "profile_photo_url")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)
