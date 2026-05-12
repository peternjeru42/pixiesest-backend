from rest_framework import serializers


class VerifyPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)


class ClientLoginSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField()
    name = serializers.CharField(required=False, allow_blank=True)


class DownloadPinSerializer(serializers.Serializer):
    collection_id = serializers.UUIDField()
    pin = serializers.CharField(write_only=True)
