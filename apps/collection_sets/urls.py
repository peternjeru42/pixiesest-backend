from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CollectionSetListCreateView, CollectionSetViewSet

router = DefaultRouter()
router.register("sets", CollectionSetViewSet, basename="set")

urlpatterns = [
    path("collections/<uuid:collection_id>/sets/", CollectionSetListCreateView.as_view(), name="collection-sets"),
]
urlpatterns += router.urls
