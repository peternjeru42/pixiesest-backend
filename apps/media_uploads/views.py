import logging

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from rest_framework import generics, permissions, status, views
from rest_framework.response import Response

from apps.storage.services import generate_presigned_upload_url, upload_bytes, using_local_storage

from .models import MediaUploadSession
from .serializers import (
    BulkCompleteUploadSerializer,
    BulkPresignUploadSerializer,
    CancelUploadSerializer,
    CompleteUploadSerializer,
    PresignUploadSerializer,
    UploadSessionSerializer,
)
from .services import complete_upload, create_upload_session

logger = logging.getLogger(__name__)


def upload_url_for_request(request, session):
    if using_local_storage():
        return request.build_absolute_uri(reverse("upload-file", kwargs={"upload_id": session.upload_id}))
    return generate_presigned_upload_url(session.r2_object_key, session.mime_type)


class PresignUploadView(views.APIView):
    def post(self, request):
        serializer = PresignUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = create_upload_session(request.user, **serializer.validated_data)
        return Response(
            {"upload": UploadSessionSerializer(session).data, "upload_url": upload_url_for_request(request, session)},
            status=status.HTTP_201_CREATED,
        )


class LocalUploadFileView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def put(self, request, upload_id):
        if not using_local_storage():
            raise Http404

        session = get_object_or_404(MediaUploadSession.objects.select_related("media_asset"), upload_id=upload_id)
        if session.expires_at <= timezone.now() or session.status in {"cancelled", "expired"}:
            return Response({"detail": "Upload session is no longer active."}, status=status.HTTP_400_BAD_REQUEST)

        body = request.body
        if len(body) != session.file_size_bytes:
            return Response({"detail": "Uploaded file size does not match the upload session."}, status=status.HTTP_400_BAD_REQUEST)

        upload_bytes(session.r2_object_key, body, session.mime_type)
        session.status = "uploaded"
        session.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CompleteUploadView(views.APIView):
    def post(self, request):
        serializer = CompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload_id = serializer.validated_data["upload_id"]
        try:
            session = complete_upload(request.user, **serializer.validated_data)
        except MediaUploadSession.DoesNotExist:
            logger.warning("Upload completion requested for missing session.", extra={"upload_id": upload_id, "user_id": str(request.user.id)})
            return Response({"detail": "Upload session was not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Upload completion failed.", extra={"upload_id": upload_id, "user_id": str(request.user.id)})
            return Response({"detail": "Unable to complete upload. Check backend logs for upload completion failure."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(UploadSessionSerializer(session).data)


class CancelUploadView(views.APIView):
    def post(self, request):
        serializer = CancelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        MediaUploadSession.objects.filter(upload_id=serializer.validated_data["upload_id"], owner=request.user).update(status="cancelled")
        return Response({"detail": "Upload cancelled."})


class UploadSessionDetailView(generics.RetrieveAPIView):
    serializer_class = UploadSessionSerializer
    lookup_field = "upload_id"
    lookup_url_kwarg = "upload_id"

    def get_queryset(self):
        return MediaUploadSession.objects.filter(owner=self.request.user).select_related("media_asset", "collection", "set")


class UploadSessionStatusView(UploadSessionDetailView):
    pass


class BulkPresignUploadView(views.APIView):
    def post(self, request):
        serializer = BulkPresignUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = []
        for item in serializer.validated_data["files"]:
            session = create_upload_session(request.user, **item)
            results.append({"upload": UploadSessionSerializer(session).data, "upload_url": upload_url_for_request(request, session)})
        return Response({"uploads": results}, status=status.HTTP_201_CREATED)


class BulkCompleteUploadView(views.APIView):
    def post(self, request):
        serializer = BulkCompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sessions = [complete_upload(request.user, **item) for item in serializer.validated_data["uploads"]]
        except MediaUploadSession.DoesNotExist:
            logger.warning("Bulk upload completion requested for missing session.", extra={"user_id": str(request.user.id)})
            return Response({"detail": "One or more upload sessions were not found."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Bulk upload completion failed.", extra={"user_id": str(request.user.id)})
            return Response({"detail": "Unable to complete uploads. Check backend logs for upload completion failure."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"uploads": UploadSessionSerializer(sessions, many=True).data})
