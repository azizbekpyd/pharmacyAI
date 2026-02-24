"""
Template URL configuration for sales app.
"""
from django.urls import path
from .views_template import (
    sales_list_view, sales_analytics_view, sales_forecast_view
)

# No app_name to avoid namespace conflicts with API URLs
# URLs are accessed via the path prefix in main urls.py

urlpatterns = [
    path('', sales_list_view, name='sales-list'),
    path('analytics/', sales_analytics_view, name='sales-analytics'),
    path('forecast/', sales_forecast_view, name='sales-forecast'),
]
