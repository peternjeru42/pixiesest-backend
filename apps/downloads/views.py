from rest_framework import generics, permissions, status, views
from rest_framework.response import Response

from apps.collections.models import Collection
from apps.favorites.models import FavoriteList
from apps.gallery_access.services import has_collection_access
from apps.media_assets.models import MediaAsset
from apps.storage.services import generate_presigned_download_url

from .models import DownloadJob, DownloadLog
from .serializers import DownloadJobSerializer, DownloadLogSerializer, DownloadRequestSerializer
from .services import create_zip_job, signed_single_download, validate_download_access
from .tasks import (
    generate_collection_original_zip,
    generate_collection_web_size_zip,
    generate_favorites_original_zip,
    generate_favorites_web_size_zip,
)


class PublicSingleDownloadView(views.APIView):
    permission_classes = [permissions.AllowAny]
    quality = "original"

    def post(self, request, media_id):
        serializer = DownloadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        asset = MediaAsset.objects.select_related("collection", "collection__download_settings", "set").get(id=media_id, status="ready")
        url = signed_single_download(request, asset, self.quality, serializer.validated_data.get("pin", ""))
        return Response({"url": url})


class PublicCollectionZipView(views.APIView):
    permission_classes = [permissions.AllowAny]
    quality = "original"

    def post(self, request, collection_slug):
        serializer = DownloadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collection = Collection.objects.select_related("download_settings").get(slug=collection_slug, status="published")
        download_type = "gallery_original_zip" if self.quality == "original" else "gallery_web_size_zip"
        job = create_zip_job(request, collection, download_type, self.quality, pin=serializer.validated_data.get("pin", ""))
        task = generate_collection_original_zip if self.quality == "original" else generate_collection_web_size_zip
        task.delay(str(job.id))
        return Response(DownloadJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class PublicFavoriteZipView(views.APIView):
    permission_classes = [permissions.AllowAny]
    quality = "original"

    def post(self, request, favorite_list_id):
        serializer = DownloadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        favorite = FavoriteList.objects.select_related("collection", "collection__download_settings").get(id=favorite_list_id)
        download_type = "favorites_original_zip" if self.quality == "original" else "favorites_web_size_zip"
        job = create_zip_job(
            request, favorite.collection, download_type, self.quality, favorite_list=favorite, pin=serializer.validated_data.get("pin", "")
        )
        task = generate_favorites_original_zip if self.quality == "original" else generate_favorites_web_size_zip
        task.delay(str(job.id))
        return Response(DownloadJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class PublicDownloadJobDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = DownloadJobSerializer
    lookup_url_kwarg = "job_id"
    queryset = DownloadJob.objects.select_related("collection", "collection__download_settings")

    def get_object(self):
        job = super().get_object()
        has_collection_access(self.request, job.collection)
        return job


class PublicDownloadJobSignedUrlView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, job_id):
        job = DownloadJob.objects.select_related("collection").get(id=job_id, status="completed")
        has_collection_access(request, job.collection)
        return Response({"url": generate_presigned_download_url(job.zip_file_key, f"{job.collection.slug}.zip")})


class AdminDownloadLogListView(generics.ListAPIView):
    serializer_class = DownloadLogSerializer

    def get_queryset(self):
        return DownloadLog.objects.filter(collection_id=self.kwargs["collection_id"], collection__owner=self.request.user)


class AdminDownloadJobListView(generics.ListAPIView):
    serializer_class = DownloadJobSerializer

    def get_queryset(self):
        return DownloadJob.objects.filter(collection_id=self.kwargs["collection_id"], collection__owner=self.request.user)


class AdminDownloadJobDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DownloadJobSerializer
    lookup_url_kwarg = "job_id"

    def get_queryset(self):
        return DownloadJob.objects.filter(collection__owner=self.request.user)


class AdminDownloadJobRetryView(views.APIView):
    def post(self, request, job_id):
        job = DownloadJob.objects.get(id=job_id, collection__owner=request.user)
        if job.download_quality == "original" and "favorites" in job.download_type:
            generate_favorites_original_zip.delay(str(job.id))
        elif job.download_quality == "original":
            generate_collection_original_zip.delay(str(job.id))
        elif "favorites" in job.download_type:
            generate_favorites_web_size_zip.delay(str(job.id))
        else:
            generate_collection_web_size_zip.delay(str(job.id))
        return Response({"detail": "Download job requeued."})
