from rest_framework import decorators, response, viewsets

from apps.core.permissions import IsStaffUser

from .models import MediaProcessingJob
from .serializers import MediaProcessingJobSerializer


class MediaProcessingJobViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MediaProcessingJobSerializer
    permission_classes = [IsStaffUser]
    lookup_url_kwarg = "job_id"

    def get_queryset(self):
        return MediaProcessingJob.objects.select_related("media_asset", "media_asset__owner")

    @decorators.action(detail=True, methods=["post"])
    def retry(self, request, job_id=None):
        from .tasks import process_uploaded_media

        job = self.get_object()
        process_uploaded_media.delay(str(job.media_asset_id))
        return response.Response({"detail": "Processing job requeued."})
