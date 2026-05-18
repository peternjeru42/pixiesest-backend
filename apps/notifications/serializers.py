from rest_framework import serializers

from .models import EmailLog, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = "__all__"
        read_only_fields = ["id", "owner", "created_at", "updated_at"]


class EmailLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailLog
        fields = "__all__"
        read_only_fields = [field.name for field in EmailLog._meta.fields]


class UnreadNotificationSerializer(serializers.ModelSerializer):
    collection_title = serializers.CharField(source="collection.title", read_only=True, default="")

    class Meta:
        model = EmailLog
        fields = [
            "id",
            "recipient_email",
            "email_type",
            "status",
            "error_message",
            "sent_at",
            "created_at",
            "collection",
            "collection_title",
        ]
        read_only_fields = fields


class MarkNotificationsReadSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)


class SendInviteSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=1200)


class SendReminderSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(required=False)
