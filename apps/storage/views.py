from rest_framework import permissions, views
from rest_framework.response import Response

from .services import get_r2_client


class StorageHealthView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        get_r2_client()
        return Response({"status": "configured"})
