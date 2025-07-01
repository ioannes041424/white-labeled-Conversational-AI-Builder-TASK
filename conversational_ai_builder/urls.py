"""
URL configuration for Conversational AI Builder project.

This file defines the main URL routing for the entire application.
It includes the Django admin interface and delegates all other URLs
to the bots application, which handles the core functionality.

URL Structure:
- /admin/ - Django admin interface for managing bots and conversations
- / - All other URLs handled by bots.urls (bot management, chat interface)

Static and Media Files:
- In development: Django serves static and media files directly
- In production: WhiteNoise middleware handles static files, media files served by web server

For more information on Django URL configuration:
https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ========================================
# MAIN URL PATTERNS
# ========================================

urlpatterns = [
    # Django admin interface for database management
    # Accessible at /admin/ with superuser credentials
    path('admin/', admin.site.urls),

    # All application URLs handled by the bots app
    # This includes bot management, chat interface, and API endpoints
    path('', include('bots.urls')),
]

# ========================================
# DEVELOPMENT STATIC FILE SERVING
# ========================================

# Serve media and static files during development
# In production, these are handled by the web server (nginx/apache) or CDN
if settings.DEBUG:
    # Serve uploaded media files (audio files, user uploads)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Serve static files (CSS, JavaScript, images)
    # Note: In production, WhiteNoise middleware handles this
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
