"""
API views for medicines app.

Handles CRUD operations for medicines and categories, plus expiry alerts.
"""
from datetime import timedelta

from django.db.models import F
from django.utils import timezone
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tenants.mixins import TenantScopedQuerysetMixin
from .models import Category, Medicine
from .serializers import CategorySerializer, MedicineListSerializer, MedicineSerializer


class CategoryViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Category model.

    Provides CRUD operations for medicine categories.
    """

    queryset = Category.objects.select_related("pharmacy").all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return self.get_tenant_queryset(super().get_queryset())


class MedicineViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Medicine model.

    Provides CRUD operations for medicines with filtering and search.
    """

    queryset = Medicine.objects.select_related("category", "pharmacy").all()
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "description"]
    ordering_fields = ["name", "unit_price", "expiry_date", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return MedicineListSerializer
        return MedicineSerializer

    def get_queryset(self):
        queryset = self.get_tenant_queryset(super().get_queryset())

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        expiring_soon = self.request.query_params.get("expiring_soon")
        if expiring_soon == "true":
            threshold = timezone.now().date() + timedelta(days=30)
            queryset = queryset.filter(
                expiry_date__lte=threshold,
                expiry_date__gte=timezone.now().date(),
            )

        expired = self.request.query_params.get("expired")
        if expired == "true":
            queryset = queryset.filter(expiry_date__lt=timezone.now().date())

        low_stock = self.request.query_params.get("low_stock")
        if low_stock == "true":
            from apps.inventory.models import Inventory

            low_stock_medicines = Inventory.objects.filter(
                pharmacy_id__in=queryset.values_list("pharmacy_id", flat=True).distinct(),
                current_stock__lt=F("min_stock_level"),
            ).values_list("medicine_id", flat=True)
            queryset = queryset.filter(id__in=low_stock_medicines)

        return queryset

    @action(detail=False, methods=["get"])
    def expiring_soon(self, request):
        days = int(request.query_params.get("days", 30))
        threshold = timezone.now().date() + timedelta(days=days)

        medicines = self.get_queryset().filter(
            expiry_date__lte=threshold,
            expiry_date__gte=timezone.now().date(),
        ).order_by("expiry_date")

        serializer = self.get_serializer(medicines, many=True)
        return Response({"count": medicines.count(), "days": days, "medicines": serializer.data})

    @action(detail=False, methods=["get"])
    def expired(self, request):
        medicines = self.get_queryset().filter(expiry_date__lt=timezone.now().date()).order_by("expiry_date")
        serializer = self.get_serializer(medicines, many=True)
        return Response({"count": medicines.count(), "medicines": serializer.data})

