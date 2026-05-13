from rest_framework import serializers

from .models import UserProfile, UserProfileStats


class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    profile_photo_url = serializers.URLField(source="user.profile_photo_url", read_only=True)

    class Meta:
        model = UserProfile
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class UserProfileStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfileStats
        fields = "__all__"
        read_only_fields = ["id", "user", "created_at", "updated_at"]
