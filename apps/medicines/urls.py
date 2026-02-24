"""
URL configuration for medicines app.
"""
from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import CategoryViewSet, MedicineViewSet

app_name = 'medicines'

router = SimpleRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'medicines', MedicineViewSet, basename='medicine')

urlpatterns = [
    path('', include(router.urls)),
]
