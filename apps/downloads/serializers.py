from rest_framework import serializers

from .models import DownloadJob, DownloadLog


class DownloadJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownloadJob
        fields = "__all__"
        read_only_fields = [field.name for field in DownloadJob._meta.fields]


class DownloadLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DownloadLog
        fields = "__all__"
        read_only_fields = [field.name for field in DownloadLog._meta.fields]


class DownloadRequestSerializer(serializers.Serializer):
    pin = serializers.CharField(required=False, allow_blank=True, write_only=True)
