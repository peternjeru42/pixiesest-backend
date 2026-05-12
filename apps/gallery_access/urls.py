from django.urls import path

from .views import (
    ClientLoginView,
    CollectionVerifyView,
    DownloadPinVerifyView,
    FolderVerifyView,
    GalleryLogoutView,
    GallerySessionRefreshView,
    GallerySessionView,
)

urlpatterns = [
    path("collections/<slug:collection_slug>/verify/", CollectionVerifyView.as_view(), name="gallery-collection-verify"),
    path("folders/<slug:folder_slug>/verify/", FolderVerifyView.as_view(), name="gallery-folder-verify"),
    path("collections/<slug:collection_slug>/client-login/", ClientLoginView.as_view(), name="gallery-client-login"),
    path("collections/<slug:collection_slug>/logout/", GalleryLogoutView.as_view(), name="gallery-logout"),
    path("session/", GallerySessionView.as_view(), name="gallery-session"),
    path("session/refresh/", GallerySessionRefreshView.as_view(), name="gallery-session-refresh"),
    path("download-pin/verify/", DownloadPinVerifyView.as_view(), name="download-pin-verify"),
]
