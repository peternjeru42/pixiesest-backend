from django.contrib import admin

from .models import EmailLog, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("template_type", "owner", "subject", "is_active")
    list_filter = ("template_type", "is_active")
    search_fields = ("subject", "owner__email")


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ("recipient_email", "email_type", "status", "owner", "created_at")
    list_filter = ("email_type", "status")
    search_fields = ("recipient_email", "owner__email")
