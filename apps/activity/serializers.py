from rest_framework import serializers

from .models import ActivityEvent


class ActivityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityEvent
        fields = "__all__"
        read_only_fields = [field.name for field in ActivityEvent._meta.fields]
