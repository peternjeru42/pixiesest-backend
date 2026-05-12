from rest_framework import serializers

from .models import MediaProcessingJob


class MediaProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaProcessingJob
        fields = "__all__"
        read_only_fields = fields
