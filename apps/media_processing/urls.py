from rest_framework.routers import DefaultRouter

from .views import MediaProcessingJobViewSet

router = DefaultRouter()
router.register("jobs", MediaProcessingJobViewSet, basename="processing-job")
urlpatterns = router.urls
