from rest_framework import serializers

from .models import StorageQuota, StorageUsageLog


class StorageQuotaSerializer(serializers.ModelSerializer):
    storage_remaining_bytes = serializers.SerializerMethodField()

    class Meta:
        model = StorageQuota
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_storage_remaining_bytes(self, obj):
        return max(0, obj.storage_limit_bytes - obj.storage_used_bytes)


class StorageUsageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageUsageLog
        fields = "__all__"
        read_only_fields = ["id", "user", "media_asset", "created_at"]
