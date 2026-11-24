from rest_framework.routers import DefaultRouter

from .views import (
    AttachmentViewSet,
    AuditLogViewSet,
    DependencyViewSet,
    ItemViewSet,
    RevisionViewSet,
    SuggestionViewSet,
)

app_name = "fmea"

router = DefaultRouter()
router.register("revisions", RevisionViewSet, basename="revision")
router.register("items", ItemViewSet, basename="item")
router.register("dependencies", DependencyViewSet, basename="dependency")
router.register("attachments", AttachmentViewSet, basename="attachment")
router.register("suggestions", SuggestionViewSet, basename="suggestion")
router.register("audit", AuditLogViewSet, basename="audit")

urlpatterns = router.urls
