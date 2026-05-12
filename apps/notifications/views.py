from rest_framework import generics, status, views
from rest_framework.response import Response

from apps.collections.models import Collection
from apps.favorites.models import FavoriteList

from .models import EmailLog, NotificationTemplate
from .serializers import EmailLogSerializer, NotificationTemplateSerializer, SendInviteSerializer, SendReminderSerializer
from .tasks import send_collection_invite_email


class SendCollectionInviteView(views.APIView):
    def post(self, request, collection_id):
        collection = Collection.objects.get(id=collection_id, owner=request.user)
        serializer = SendInviteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_collection_invite_email.delay(str(collection.id), serializer.validated_data["recipient_email"])
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
