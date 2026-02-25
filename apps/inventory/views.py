"""
API views for inventory app.

Handles CRUD operations for inventory and reorder recommendations.
"""
from django.db.models import F
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import InventoryRolePermission, ReorderRecommendationRolePermission
from apps.tenants.mixins import TenantScopedQuerysetMixin
from apps.tenants.models import Pharmacy
from apps.tenants.utils import require_user_pharmacy
from .models import Inventory, ReorderRecommendation
from .serializers import (
    InventoryListSerializer,
    InventorySerializer,
    ReorderRecommendationCreateSerializer,
    ReorderRecommendationSerializer,
)
from .services import InventoryService


class InventoryViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Inventory.objects.select_related("medicine", "pharmacy").all()
    permission_classes = [InventoryRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["medicine__name", "medicine__sku"]
    ordering_fields = ["current_stock", "medicine__name", "created_at"]
    ordering = ["medicine__name"]

    def get_serializer_class(self):
        if self.action == "list":
            return InventoryListSerializer
        return InventorySerializer

    def get_queryset(self):
        queryset = self.get_tenant_queryset(super().get_queryset())

        needs_reorder = self.request.query_params.get("needs_reorder")
        if needs_reorder == "true":
            queryset = queryset.filter(current_stock__lt=F("min_stock_level"))

        low_stock = self.request.query_params.get("low_stock")
        if low_stock == "true":
            queryset = queryset.filter(current_stock__lt=F("min_stock_level"))

        return queryset

    @action(detail=True, methods=["post"])
    def update_stock(self, request, pk=None):
        inventory = self.get_object()
        quantity = request.data.get("quantity")
        operation = request.data.get("operation", "set")

        if quantity is None:
            return Response({"error": "Quantity is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"error": "Quantity must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        if operation == "set":
            inventory.current_stock = quantity
        elif operation == "add":
            inventory.current_stock += quantity
        elif operation == "subtract":
            inventory.current_stock = max(0, inventory.current_stock - quantity)
        else:
            return Response(
                {"error": 'Invalid operation. Use "set", "add", or "subtract"'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inventory.last_restocked_date = timezone.now()
        inventory.save()

        serializer = self.get_serializer(inventory)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def reorder_recommendations(self, request):
        if request.user.is_superuser:
            pharmacy_id = request.query_params.get("pharmacy_id")
            if not pharmacy_id:
                return Response(
                    {"error": "pharmacy_id is required for superuser"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pharmacy = Pharmacy.objects.filter(id=pharmacy_id).first()
            if pharmacy is None:
                return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            pharmacy = require_user_pharmacy(request.user)

        recommendations = InventoryService.generate_reorder_recommendations(pharmacy=pharmacy)
        serializer = ReorderRecommendationSerializer(recommendations, many=True, context={"request": request})
        return Response({"count": len(recommendations), "recommendations": serializer.data}, status=status.HTTP_200_OK)


class ReorderRecommendationViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = ReorderRecommendation.objects.select_related("medicine", "approved_by", "pharmacy").all()
    serializer_class = ReorderRecommendationSerializer
    permission_classes = [ReorderRecommendationRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["medicine__name", "medicine__sku", "reason"]
    ordering_fields = ["priority", "status", "created_at"]
    ordering = ["-priority", "-created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return ReorderRecommendationCreateSerializer
        return ReorderRecommendationSerializer

    def get_queryset(self):
        queryset = self.get_tenant_queryset(super().get_queryset())

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = self.request.query_params.get("priority")
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        recommendation = self.get_object()
        if recommendation.status != "PENDING":
            return Response({"error": "Only pending recommendations can be approved"}, status=status.HTTP_400_BAD_REQUEST)

        recommendation.status = "APPROVED"
        recommendation.approved_by = request.user
        recommendation.approved_at = timezone.now()
        recommendation.save()

        try:
            inventory = Inventory.objects.get(
                medicine=recommendation.medicine,
                pharmacy=recommendation.pharmacy,
            )
            inventory.current_stock += recommendation.recommended_quantity
            inventory.last_restocked_date = timezone.now()
            inventory.save()
        except Inventory.DoesNotExist:
            pass

        serializer = self.get_serializer(recommendation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        recommendation = self.get_object()
        if recommendation.status != "PENDING":
            return Response({"error": "Only pending recommendations can be rejected"}, status=status.HTTP_400_BAD_REQUEST)

        recommendation.status = "REJECTED"
        recommendation.save()
        serializer = self.get_serializer(recommendation)
        return Response(serializer.data, status=status.HTTP_200_OK)
