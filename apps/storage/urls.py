from django.urls import path

from .views import StorageHealthView

urlpatterns = [path("health/", StorageHealthView.as_view(), name="storage-health")]
