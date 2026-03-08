"""
URL configuration for pharmacy_ai project.
"""
from django.contrib import admin
from django.conf.urls import include
from django.conf.urls.i18n import i18n_patterns, set_language
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from django.shortcuts import redirect
from apps.accounts.views import logout_view, start_trial_view
from pharmacy_ai.views import landing_entry_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # Redirect old login URL for compatibility
    path('accounts/login/', lambda request: redirect('/login/', permanent=False)),

    # API endpoints (REST API)
    path('api/auth/', include('apps.accounts.urls_api')),  # API authentication endpoints
    path('api/medicines/', include('apps.medicines.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/pos/', include('apps.pos_integration.urls')),
]

# i18n endpoints (set_language and javascript_catalog)
urlpatterns += [
    path('i18n/', include('django.conf.urls.i18n')),
]

# Frontend/template routes (localized)
urlpatterns += i18n_patterns(
    path('', landing_entry_view, name='landing'),
    path('start-trial/', start_trial_view, name='start-trial'),
    path('login/', include('apps.accounts.urls')),  # Frontend login page
    path('logout/', logout_view, name='logout'),  # Frontend logout
    path('dashboard/', include('apps.dashboard.urls')),
    path('medicines/', include('apps.medicines.urls_template')),
    path('sales/', include('apps.sales.urls_template')),
    path('inventory/', include('apps.inventory.urls_template')),
    prefix_default_language=False,
)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
