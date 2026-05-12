from django.urls import path

from .views import (
    EmailLogListView,
    NotificationTemplateDetailView,
    NotificationTemplateListCreateView,
    SendCollectionInviteView,
    SendFavoriteReminderView,
)

urlpatterns = [
    path("collections/<uuid:collection_id>/send-invite/", SendCollectionInviteView.as_view(), name="collection-send-invite"),
    path("favorites/<uuid:favorite_list_id>/send-reminder/", SendFavoriteReminderView.as_view(), name="favorite-send-reminder"),
    path("notifications/email-logs/", EmailLogListView.as_view(), name="email-logs"),
    path("notifications/templates/", NotificationTemplateListCreateView.as_view(), name="notification-templates"),
    path("notifications/templates/<uuid:template_id>/", NotificationTemplateDetailView.as_view(), name="notification-template-detail"),
]
