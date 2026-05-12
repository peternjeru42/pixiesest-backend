from rest_framework import generics, views
from rest_framework.response import Response

from .models import StorageQuota, StorageUsageLog
from .serializers import StorageQuotaSerializer, StorageUsageLogSerializer


class QuotaView(generics.RetrieveAPIView):
    serializer_class = StorageQuotaSerializer

    def get_object(self):
        return StorageQuota.objects.get_or_create(user=self.request.user)[0]


class QuotaStorageView(views.APIView):
    def get(self, request):
        quota = StorageQuota.objects.get_or_create(user=request.user)[0]
        return Response(StorageQuotaSerializer(quota).data)


class UsageLogListView(generics.ListAPIView):
    serializer_class = StorageUsageLogSerializer

    def get_queryset(self):
        return StorageUsageLog.objects.filter(user=self.request.user).select_related("media_asset")
