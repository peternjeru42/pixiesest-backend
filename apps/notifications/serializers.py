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


class SendInviteSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField()
    message = serializers.CharField(required=False, allow_blank=True, max_length=1200)


class SendReminderSerializer(serializers.Serializer):
    recipient_email = serializers.EmailField(required=False)
