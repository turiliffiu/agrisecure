"""
AgriSecure IoT System - Main URLs
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include('apps.api.urls')),
    
    # Health check
    path('health/', include('apps.core.urls')),
    
    # Frontend
    path('', include('apps.frontend.urls')), 
]

# Static/Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin customization
admin.site.site_header = 'AgriSecure IoT Admin'
admin.site.site_title = 'AgriSecure'
admin.site.index_title = 'Pannello di Controllo'
