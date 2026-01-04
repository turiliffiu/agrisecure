"""
AgriSecure IoT System - API URLs

Routing per tutte le API REST
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from .views import (
    NodeViewSet,
    SensorReadingViewSet,
    SensorAlertViewSet,
    SecurityEventViewSet,
    AlarmViewSet,
    SystemArmViewSet,
    SecurityZoneViewSet,
    DashboardSummaryView,
    DashboardChartsView,
)

# Router per ViewSets
router = DefaultRouter()
router.register(r'nodes', NodeViewSet, basename='node')
router.register(r'sensors/readings', SensorReadingViewSet, basename='sensor-reading')
router.register(r'sensors/alerts', SensorAlertViewSet, basename='sensor-alert')
router.register(r'security/events', SecurityEventViewSet, basename='security-event')
router.register(r'security/alarms', AlarmViewSet, basename='alarm')
router.register(r'security/arm', SystemArmViewSet, basename='system-arm')
router.register(r'security/zones', SecurityZoneViewSet, basename='security-zone')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),
    
    # Dashboard
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('dashboard/charts/', DashboardChartsView.as_view(), name='dashboard-charts'),
    
    # Authentication - JWT
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # OpenAPI Schema & Documentation
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
