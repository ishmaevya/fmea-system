from rest_framework.routers import DefaultRouter

from .views import ComponentViewSet, ProductVariantViewSet, ProductViewSet

app_name = "catalog"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("variants", ProductVariantViewSet, basename="variant")
router.register("components", ComponentViewSet, basename="component")

urlpatterns = router.urls
