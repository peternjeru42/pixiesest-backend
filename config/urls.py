from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health_check(_request):
    return JsonResponse({"status": "ok", "service": "pixieset-backend"})


urlpatterns = [
    path("", health_check, name="root-health"),
    path("health/", health_check, name="health"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/profile/", include("apps.profiles.urls")),
    path("api/v1/quotas/", include("apps.quotas.urls")),
    path("api/v1/folders/", include("apps.folders.urls")),
    path("api/v1/collections/", include("apps.collections.urls")),
    path("api/v1/", include("apps.collection_sets.urls")),
    path("api/v1/storage/", include("apps.storage.urls")),
    path("api/v1/", include("apps.media_assets.urls")),
    path("api/v1/uploads/", include("apps.media_uploads.urls")),
    path("api/v1/processing/", include("apps.media_processing.urls")),
    path("api/v1/gallery-access/", include("apps.gallery_access.urls")),
    path("api/v1/public/", include("apps.public_gallery.urls")),
    path("api/v1/", include("apps.favorites.urls")),
    path("api/v1/", include("apps.downloads.urls")),
    path("api/v1/", include("apps.activity.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/dashboard/", include("apps.admin_dashboard.urls")),
]
