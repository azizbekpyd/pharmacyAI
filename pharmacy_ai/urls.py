"""
URL configuration for pharmacy_ai project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.shortcuts import redirect
from apps.accounts.views import logout_view, start_trial_view
from pharmacy_ai.views import landing_entry_view

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Redirect old login URL for compatibility
    path('accounts/login/', lambda request: redirect('/login/', permanent=False)),
    
    # Frontend routes (template views)
    path('', landing_entry_view, name='landing'),
    path('start-trial/', start_trial_view, name='start-trial'),
    path('login/', include('apps.accounts.urls')),  # Frontend login page
    path('logout/', logout_view, name='logout'),  # Frontend logout
    path('dashboard/', include('apps.dashboard.urls')),
    path('medicines/', include('apps.medicines.urls_template')),
    path('sales/', include('apps.sales.urls_template')),
    path('inventory/', include('apps.inventory.urls_template')),
    
    # API endpoints (REST API)
    path('api/auth/', include('apps.accounts.urls_api')),  # API authentication endpoints
    path('api/medicines/', include('apps.medicines.urls')),
    path('api/sales/', include('apps.sales.urls')),
    path('api/inventory/', include('apps.inventory.urls')),
    path('api/pos/', include('apps.pos_integration.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
