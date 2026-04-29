"""
Template URL configuration for inventory app.
"""
from django.urls import path
from .views_template import (
    activity_log_view,
    inventory_list_view,
    purchases_view,
    reorder_recommendations_view,
    stock_movements_view,
)

# No app_name to avoid namespace conflicts with API URLs
# URLs are accessed via the path prefix in main urls.py

urlpatterns = [
    path('', inventory_list_view, name='inventory-list'),
    path('reorder-recommendations/', reorder_recommendations_view, name='inventory-reorder-recommendations'),
    path('stock-movements/', stock_movements_view, name='inventory-stock-movements'),
    path('purchases/', purchases_view, name='inventory-purchases'),
    path('activity-log/', activity_log_view, name='inventory-activity-log'),
]
