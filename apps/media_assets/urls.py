from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CollectionMediaListView, MediaAssetViewSet, SetMediaListView

router = DefaultRouter()
router.register("media", MediaAssetViewSet, basename="media")

urlpatterns = [
    path("collections/<uuid:collection_id>/media/", CollectionMediaListView.as_view(), name="collection-media"),
    path("sets/<uuid:set_id>/media/", SetMediaListView.as_view(), name="set-media"),
]
urlpatterns += router.urls
