from rest_framework.routers import DefaultRouter
from .views import ScenarioViewSet, LineItemViewSet

router = DefaultRouter()
router.register("scenarios", ScenarioViewSet, basename="scenario")
router.register("line-items", LineItemViewSet, basename="lineitem")

urlpatterns = router.urls
