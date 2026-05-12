from django.urls import path

from .views import ProfileStatsView, ProfileStorageView, ProfileView, RecentActivityView

urlpatterns = [
    path("", ProfileView.as_view(), name="profile"),
    path("stats/", ProfileStatsView.as_view(), name="profile-stats"),
    path("storage/", ProfileStorageView.as_view(), name="profile-storage"),
    path("recent-activity/", RecentActivityView.as_view(), name="profile-recent-activity"),
]
