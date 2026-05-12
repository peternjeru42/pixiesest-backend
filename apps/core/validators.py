from django.conf import settings
from rest_framework import serializers


def validate_upload_mime_type(mime_type):
    if mime_type not in settings.ALLOWED_UPLOAD_MIME_TYPES:
        raise serializers.ValidationError("Unsupported upload mime type.")


def validate_upload_file_size(size):
    if size <= 0:
        raise serializers.ValidationError("File size must be greater than zero.")
    if size > settings.MAX_UPLOAD_FILE_SIZE_BYTES:
        raise serializers.ValidationError("File exceeds maximum upload size.")
