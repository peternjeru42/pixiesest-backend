from django.contrib.auth.hashers import check_password
from rest_framework import permissions, views
from rest_framework.response import Response

from apps.collections.models import Collection
from apps.folders.models import Folder

from .serializers import ClientLoginSerializer, DownloadPinSerializer, VerifyPasswordSerializer
from .services import (
    AccessAttempt,
    create_gallery_session,
    get_gallery_session,
    verify_client_password,
    verify_collection_password,
    verify_folder_password,
)


class CollectionVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "gallery_verify"

    def post(self, request, collection_slug):
        serializer = VerifyPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collection = Collection.objects.select_related("privacy_settings").get(slug=collection_slug, status="published")
        token = verify_collection_password(request, collection, serializer.validated_data["password"], serializer.validated_data.get("email", ""))
        return Response({"gallery_session": token})


class FolderVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "gallery_verify"

    def post(self, request, folder_slug):
        serializer = VerifyPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        folder = Folder.objects.get(slug=folder_slug)
        token = verify_folder_password(request, folder, serializer.validated_data["password"], serializer.validated_data.get("email", ""))
        return Response({"gallery_session": token})


class ClientLoginView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "gallery_verify"

    def post(self, request, collection_slug):
        serializer = ClientLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collection = Collection.objects.select_related("privacy_settings").get(slug=collection_slug, status="published")
        token = verify_client_password(
            request,
            collection,
            serializer.validated_data["password"],
            serializer.validated_data["email"],
            serializer.validated_data.get("name", ""),
        )
        return Response({"gallery_session": token})


class GalleryLogoutView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, collection_slug):
        return Response({"detail": "Client should discard gallery session token."})


class GallerySessionView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        session = get_gallery_session(request)
        return Response({"active": bool(session), "access_type": session.access_type if session else None})


class GallerySessionRefreshView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        session = get_gallery_session(request)
        if not session:
            return Response({"active": False}, status=403)
        token = create_gallery_session(
            request,
            collection=session.collection,
            folder=session.folder,
            client_email=session.client_email,
            client_name=session.client_name,
            access_type=session.access_type,
        )
        return Response({"gallery_session": token})


class DownloadPinVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "download_pin"

    def post(self, request):
        serializer = DownloadPinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        collection = Collection.objects.select_related("download_settings").get(id=serializer.validated_data["collection_id"])
        ok = collection.download_settings.download_pin_enabled and check_password(
            serializer.validated_data["pin"], collection.download_settings.download_pin_hash
        )
        AccessAttempt.objects.create(collection=collection, attempt_type="download_pin", success=ok)
        return Response({"valid": ok}, status=200 if ok else 403)
