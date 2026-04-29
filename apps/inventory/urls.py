"""
URL configuration for inventory app.
"""
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    ActivityLogViewSet,
    InventoryViewSet,
    PurchaseOrderViewSet,
    ReorderRecommendationViewSet,
    StockMovementViewSet,
    SupplierViewSet,
)

app_name = 'inventory'

router = SimpleRouter()
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'reorder-recommendations', ReorderRecommendationViewSet, basename='reorder-recommendation')
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'stock-movements', StockMovementViewSet, basename='stock-movement')
router.register(r'activity-logs', ActivityLogViewSet, basename='activity-log')

urlpatterns = [
    path('', include(router.urls)),
]
