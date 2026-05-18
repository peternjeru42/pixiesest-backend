from django.urls import path

from .views import (
    BulkCompleteUploadView,
    BulkPresignUploadView,
    CancelUploadView,
    CompleteUploadView,
    LocalUploadFileView,
    PresignUploadView,
    UploadSessionDetailView,
    UploadSessionStatusView,
)

urlpatterns = [
    path("presign/", PresignUploadView.as_view(), name="upload-presign"),
    path("complete/", CompleteUploadView.as_view(), name="upload-complete"),
    path("cancel/", CancelUploadView.as_view(), name="upload-cancel"),
    path("<str:upload_id>/file/", LocalUploadFileView.as_view(), name="upload-file"),
    path("<str:upload_id>/", UploadSessionDetailView.as_view(), name="upload-detail"),
    path("<str:upload_id>/status/", UploadSessionStatusView.as_view(), name="upload-status"),
    path("bulk/presign/", BulkPresignUploadView.as_view(), name="upload-bulk-presign"),
    path("bulk/complete/", BulkCompleteUploadView.as_view(), name="upload-bulk-complete"),
]
