from rest_framework.routers import DefaultRouter

from .views import RevisionViewSet

app_name = "fmea"

router = DefaultRouter()
router.register("revisions", RevisionViewSet, basename="revision")

urlpatterns = router.urls
