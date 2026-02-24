"""
URL configuration for sales app.
"""
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import SaleViewSet

app_name = 'sales'

router = SimpleRouter()
router.register(r'sales', SaleViewSet, basename='sale')

urlpatterns = [
    path('', include(router.urls)),
]
