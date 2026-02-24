"""
URL configuration for dashboard app.
"""
from django.urls import path
from .views import dashboard_view

# No app_name to avoid namespace conflicts
# URLs are accessed via the path prefix in main urls.py

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
]
