from rest_framework import generics, views
from rest_framework.response import Response

from apps.activity.serializers import ActivityEventSerializer
from apps.activity.models import ActivityEvent

from .models import UserProfile, UserProfileStats
from .serializers import UserProfileSerializer, UserProfileStatsSerializer
from .services import recalculate_user_profile_stats


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer

    def get_object(self):
        return UserProfile.objects.get_or_create(user=self.request.user)[0]


class ProfileStatsView(generics.RetrieveAPIView):
    serializer_class = UserProfileStatsSerializer

    def get_object(self):
        return recalculate_user_profile_stats(self.request.user)


class ProfileStorageView(views.APIView):
    def get(self, request):
        stats = recalculate_user_profile_stats(request.user)
        return Response(
            {
                "total_storage_bytes": stats.total_storage_bytes,
                "total_original_storage_bytes": stats.total_original_storage_bytes,
                "total_preview_storage_bytes": stats.total_preview_storage_bytes,
                "total_thumbnail_storage_bytes": stats.total_thumbnail_storage_bytes,
            }
        )


class RecentActivityView(generics.ListAPIView):
    serializer_class = ActivityEventSerializer

    def get_queryset(self):
        return ActivityEvent.objects.filter(owner=self.request.user).select_related("collection", "set", "media_asset")[:25]
