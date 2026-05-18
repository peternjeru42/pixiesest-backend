from django.utils import timezone
from rest_framework import generics, status, views
from rest_framework.response import Response

from apps.collections.models import Collection
from apps.favorites.models import FavoriteList

from .models import EmailLog, NotificationTemplate
from .serializers import (
    EmailLogSerializer,
    MarkNotificationsReadSerializer,
    NotificationTemplateSerializer,
    SendInviteSerializer,
    SendReminderSerializer,
    UnreadNotificationSerializer,
)
from .tasks import send_collection_invite_email


class SendCollectionInviteView(views.APIView):
    def post(self, request, collection_id):
        collection = Collection.objects.get(id=collection_id, owner=request.user)
        serializer = SendInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        log = EmailLog.objects.create(
            owner=request.user,
            collection=collection,
            recipient_email=serializer.validated_data["recipient_email"],
            email_type="collection_invite",
        )
        try:
            send_collection_invite_email.delay(str(log.id), serializer.validated_data.get("message", ""))
        except Exception as exc:
            log.status = "failed"
            log.error_message = f"Email queue unavailable: {exc}"
            log.save(update_fields=["status", "error_message"])
            return Response({"detail": "Email queue unavailable. The invite was not sent."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({"detail": "Invite queued."}, status=status.HTTP_202_ACCEPTED)


class SendFavoriteReminderView(views.APIView):
    def post(self, request, favorite_list_id):
        favorite = FavoriteList.objects.get(id=favorite_list_id, collection__owner=request.user)
        serializer = SendReminderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": f"Reminder queued for {serializer.validated_data.get('recipient_email') or favorite.client_email}."})


class EmailLogListView(generics.ListAPIView):
    serializer_class = EmailLogSerializer

    def get_queryset(self):
        return EmailLog.objects.filter(owner=self.request.user)


class UnreadNotificationListView(generics.ListAPIView):
    serializer_class = UnreadNotificationSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            EmailLog.objects
            .filter(owner=self.request.user, status__in=["sent", "failed"], read_at__isnull=True)
            .select_related("collection")
            .order_by("-sent_at", "-created_at")[:20]
        )


class MarkNotificationsReadView(views.APIView):
    def post(self, request):
        serializer = MarkNotificationsReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        queryset = EmailLog.objects.filter(owner=request.user, status__in=["sent", "failed"], read_at__isnull=True)
        ids = serializer.validated_data.get("ids")
        if ids:
            queryset = queryset.filter(id__in=ids)
        updated = queryset.update(read_at=timezone.now())
        return Response({"detail": "Notifications marked read.", "updated": updated})


class NotificationTemplateListCreateView(generics.ListCreateAPIView):
    serializer_class = NotificationTemplateSerializer

    def get_queryset(self):
        return NotificationTemplate.objects.filter(owner=self.request.user) | NotificationTemplate.objects.filter(owner__isnull=True)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class NotificationTemplateDetailView(generics.UpdateAPIView, generics.DestroyAPIView):
    serializer_class = NotificationTemplateSerializer
    lookup_url_kwarg = "template_id"

    def get_queryset(self):
        return NotificationTemplate.objects.filter(owner=self.request.user)
