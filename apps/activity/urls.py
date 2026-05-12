from django.urls import path

from .views import (
    ActivityListView,
    CollectionActivityListView,
    FavoriteActivityListView,
    MediaActivityListView,
    RecentActivityListView,
)

urlpatterns = [
    path("activity/", ActivityListView.as_view(), name="activity"),
    path("activity/recent/", RecentActivityListView.as_view(), name="activity-recent"),
    path("collections/<uuid:collection_id>/activity/", CollectionActivityListView.as_view(), name="collection-activity"),
    path("media/<uuid:media_id>/activity/", MediaActivityListView.as_view(), name="media-activity"),
    path("favorites/<uuid:favorite_list_id>/activity/", FavoriteActivityListView.as_view(), name="favorite-activity"),
]
