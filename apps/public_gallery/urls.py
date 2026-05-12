from django.urls import path

from .views import (
    PublicCollectionDetailView,
    PublicCollectionMediaView,
    PublicCollectionSetsView,
    PublicFolderCollectionsView,
    PublicFolderDetailView,
    PublicMediaDetailView,
    PublicMediaSignedUrlView,
    PublicMediaThumbnailUrlView,
    PublicSetDetailView,
    PublicSetMediaView,
)

urlpatterns = [
    path("folders/<slug:folder_slug>/", PublicFolderDetailView.as_view(), name="public-folder"),
    path("folders/<slug:folder_slug>/collections/", PublicFolderCollectionsView.as_view(), name="public-folder-collections"),
    path("collections/<slug:collection_slug>/", PublicCollectionDetailView.as_view(), name="public-collection"),
    path("collections/<slug:collection_slug>/sets/", PublicCollectionSetsView.as_view(), name="public-collection-sets"),
    path("collections/<slug:collection_slug>/media/", PublicCollectionMediaView.as_view(), name="public-collection-media"),
    path("sets/<slug:set_slug>/", PublicSetDetailView.as_view(), name="public-set"),
    path("sets/<slug:set_slug>/media/", PublicSetMediaView.as_view(), name="public-set-media"),
    path("media/<uuid:media_id>/", PublicMediaDetailView.as_view(), name="public-media"),
    path("media/<uuid:media_id>/thumbnail-url/", PublicMediaThumbnailUrlView.as_view(), name="public-media-thumbnail"),
    path("media/<uuid:media_id>/preview-url/", PublicMediaSignedUrlView.as_view(), name="public-media-preview"),
]
