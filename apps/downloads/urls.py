from django.urls import path

from .views import (
    AdminDownloadJobDetailView,
    AdminDownloadJobListView,
    AdminDownloadJobRetryView,
    AdminDownloadLogListView,
    PublicCollectionZipView,
    PublicDownloadJobDetailView,
    PublicDownloadJobSignedUrlView,
    PublicFavoriteZipView,
    PublicSingleDownloadView,
)

urlpatterns = [
    path("public/downloads/media/<uuid:media_id>/original/", PublicSingleDownloadView.as_view(quality="original"), name="public-download-original"),
    path("public/downloads/media/<uuid:media_id>/web-size/", PublicSingleDownloadView.as_view(quality="web_size"), name="public-download-web-size"),
    path("public/downloads/media/<uuid:media_id>/high-res/", PublicSingleDownloadView.as_view(quality="high_res"), name="public-download-high-res"),
    path("public/downloads/collections/<slug:collection_slug>/original-zip/", PublicCollectionZipView.as_view(quality="original"), name="public-download-collection-original-zip"),
    path("public/downloads/collections/<slug:collection_slug>/web-size-zip/", PublicCollectionZipView.as_view(quality="web_size"), name="public-download-collection-web-zip"),
    path("public/downloads/favorites/<uuid:favorite_list_id>/original-zip/", PublicFavoriteZipView.as_view(quality="original"), name="public-download-favorite-original-zip"),
    path("public/downloads/favorites/<uuid:favorite_list_id>/web-size-zip/", PublicFavoriteZipView.as_view(quality="web_size"), name="public-download-favorite-web-zip"),
    path("public/download-jobs/<uuid:job_id>/", PublicDownloadJobDetailView.as_view(), name="public-download-job"),
    path("public/download-jobs/<uuid:job_id>/signed-url/", PublicDownloadJobSignedUrlView.as_view(), name="public-download-job-signed-url"),
    path("collections/<uuid:collection_id>/downloads/logs/", AdminDownloadLogListView.as_view(), name="admin-download-logs"),
    path("collections/<uuid:collection_id>/downloads/jobs/", AdminDownloadJobListView.as_view(), name="admin-download-jobs"),
    path("downloads/jobs/<uuid:job_id>/", AdminDownloadJobDetailView.as_view(), name="admin-download-job"),
    path("downloads/jobs/<uuid:job_id>/retry/", AdminDownloadJobRetryView.as_view(), name="admin-download-job-retry"),
]
