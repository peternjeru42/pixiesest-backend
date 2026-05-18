from rest_framework import serializers

from apps.core.validators import validate_upload_file_size, validate_upload_mime_type


class PresignUploadSerializer(serializers.Serializer):
    collection_id = serializers.UUIDField()
    set_id = serializers.UUIDField(required=False, allow_null=True)
    original_filename = serializers.CharField(max_length=255)
    mime_type = serializers.CharField(max_length=120)
    file_size_bytes = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        validate_upload_mime_type(attrs["mime_type"])
        validate_upload_file_size(attrs["file_size_bytes"])
        return attrs


class CompleteUploadSerializer(serializers.Serializer):
    upload_id = serializers.CharField()
    checksum = serializers.CharField(required=False, allow_blank=True)


class CancelUploadSerializer(serializers.Serializer):
    upload_id = serializers.CharField()


class UploadSessionSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import MediaUploadSession

        model = MediaUploadSession
        fields = "__all__"
        read_only_fields = [field.name for field in MediaUploadSession._meta.fields]


class BulkPresignUploadSerializer(serializers.Serializer):
    files = PresignUploadSerializer(many=True)


class BulkCompleteUploadSerializer(serializers.Serializer):
    uploads = CompleteUploadSerializer(many=True)
