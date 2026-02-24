"""
Template URL configuration for inventory app.
"""
from django.urls import path
from .views_template import (
    inventory_list_view, reorder_recommendations_view
)

# No app_name to avoid namespace conflicts with API URLs
# URLs are accessed via the path prefix in main urls.py

urlpatterns = [
    path('', inventory_list_view, name='inventory-list'),
    path('reorder-recommendations/', reorder_recommendations_view, name='inventory-reorder-recommendations'),
]
