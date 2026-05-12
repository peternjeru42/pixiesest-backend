from django.urls import path

from .views import (
    ClientsSummaryView,
    CollectionsSummaryView,
    DashboardOverviewView,
    DashboardStorageView,
    MediaSummaryView,
    RecentActivityView,
    RecentDownloadsView,
    RecentFavoritesView,
    RecentUploadsView,
)

urlpatterns = [
    path("overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("storage/", DashboardStorageView.as_view(), name="dashboard-storage"),
    path("recent-uploads/", RecentUploadsView.as_view(), name="dashboard-recent-uploads"),
    path("recent-downloads/", RecentDownloadsView.as_view(), name="dashboard-recent-downloads"),
    path("recent-favorites/", RecentFavoritesView.as_view(), name="dashboard-recent-favorites"),
    path("recent-activity/", RecentActivityView.as_view(), name="dashboard-recent-activity"),
    path("collections/summary/", CollectionsSummaryView.as_view(), name="dashboard-collections-summary"),
    path("media/summary/", MediaSummaryView.as_view(), name="dashboard-media-summary"),
    path("clients/summary/", ClientsSummaryView.as_view(), name="dashboard-clients-summary"),
]
