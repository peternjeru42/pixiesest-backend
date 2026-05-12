from rest_framework import generics, status, views
from rest_framework.response import Response

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


class PresignUploadView(views.APIView):
    def post(self, request):
        serializer = PresignUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session, url = create_upload_session(request.user, **serializer.validated_data)
        return Response({"upload": UploadSessionSerializer(session).data, "upload_url": url}, status=status.HTTP_201_CREATED)


class CompleteUploadView(views.APIView):
    def post(self, request):
        serializer = CompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = complete_upload(request.user, **serializer.validated_data)
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
            session, url = create_upload_session(request.user, **item)
            results.append({"upload": UploadSessionSerializer(session).data, "upload_url": url})
        return Response({"uploads": results}, status=status.HTTP_201_CREATED)


class BulkCompleteUploadView(views.APIView):
    def post(self, request):
        serializer = BulkCompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sessions = [complete_upload(request.user, **item) for item in serializer.validated_data["uploads"]]
        return Response({"uploads": UploadSessionSerializer(sessions, many=True).data})
