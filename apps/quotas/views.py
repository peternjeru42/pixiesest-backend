from rest_framework import generics, views
from rest_framework.response import Response

from .models import StorageQuota, StorageUsageLog
from .serializers import StorageQuotaSerializer, StorageUsageLogSerializer
from .services import recalculate_storage_usage


class QuotaView(generics.RetrieveAPIView):
    serializer_class = StorageQuotaSerializer

    def get_object(self):
        return recalculate_storage_usage(self.request.user, refresh_missing=True)


class QuotaStorageView(views.APIView):
    def get(self, request):
        quota = recalculate_storage_usage(request.user, refresh_missing=True)
        return Response(StorageQuotaSerializer(quota).data)


class UsageLogListView(generics.ListAPIView):
    serializer_class = StorageUsageLogSerializer

    def get_queryset(self):
        return StorageUsageLog.objects.filter(user=self.request.user).select_related("media_asset")
