"""
URL configuration for commodity_tracker project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/market/', include('apps.market.urls')), # Include market app API URLs
    path('', include('apps.market.web_urls')), # Include market app Web URLs at root
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')), # For browsable API login
]

# Serve static and media files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Optionally add Django Debug Toolbar URLs
    # if "debug_toolbar" in settings.INSTALLED_APPS:
    #     import debug_toolbar
    #     urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns 