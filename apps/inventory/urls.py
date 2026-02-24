"""
URL configuration for inventory app.
"""
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import InventoryViewSet, ReorderRecommendationViewSet

app_name = 'inventory'

router = SimpleRouter()
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'reorder-recommendations', ReorderRecommendationViewSet, basename='reorder-recommendation')

urlpatterns = [
    path('', include(router.urls)),
]
