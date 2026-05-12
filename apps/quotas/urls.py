from django.urls import path

from .views import QuotaStorageView, QuotaView, UsageLogListView

urlpatterns = [
    path("", QuotaView.as_view(), name="quotas"),
    path("storage/", QuotaStorageView.as_view(), name="quotas-storage"),
    path("usage-logs/", UsageLogListView.as_view(), name="quotas-usage-logs"),
]
