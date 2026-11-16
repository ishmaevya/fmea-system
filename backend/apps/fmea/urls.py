from rest_framework.routers import DefaultRouter

from .views import DependencyViewSet, ItemViewSet, RevisionViewSet

app_name = "fmea"

router = DefaultRouter()
router.register("revisions", RevisionViewSet, basename="revision")
router.register("items", ItemViewSet, basename="item")
router.register("dependencies", DependencyViewSet, basename="dependency")

urlpatterns = router.urls
