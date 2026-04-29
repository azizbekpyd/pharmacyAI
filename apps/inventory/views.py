"""
API views for inventory app.

Handles CRUD operations for inventory, purchases, stock movement ledger,
audit logs, and reorder recommendations.
"""
import csv

from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import InventoryRolePermission, ReorderRecommendationRolePermission
from apps.tenants.mixins import TenantScopedQuerysetMixin
from apps.tenants.models import Pharmacy
from apps.tenants.utils import require_user_pharmacy
from .models import ActivityLog, Inventory, PurchaseOrder, ReorderRecommendation, StockMovement, Supplier
from .serializers import (
    ActivityLogSerializer,
    InventoryListSerializer,
    InventorySerializer,
    PurchaseOrderSerializer,
    ReorderRecommendationCreateSerializer,
    ReorderRecommendationSerializer,
    StockMovementSerializer,
    SupplierSerializer,
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
            return Response({"error": _("Quantity is required")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            return Response({"error": _("Quantity must be an integer")}, status=status.HTTP_400_BAD_REQUEST)

        if operation == "set":
            InventoryService.set_stock(
                inventory=inventory,
                new_quantity=quantity,
                user=request.user,
                reason=_("Manual stock count"),
            )
        elif operation == "add":
            InventoryService.adjust_stock(
                inventory=inventory,
                quantity_change=quantity,
                movement_type=StockMovement.TYPE_ADJUSTMENT,
                user=request.user,
                reason=_("Manual stock addition"),
            )
        elif operation == "subtract":
            InventoryService.adjust_stock(
                inventory=inventory,
                quantity_change=-quantity,
                movement_type=StockMovement.TYPE_ADJUSTMENT,
                user=request.user,
                reason=_("Manual stock subtraction"),
            )
        else:
            return Response(
                {"error": _('Invalid operation. Use "set", "add", or "subtract"')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(inventory)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        queryset = self.get_queryset().select_related("medicine")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="inventory.csv"'
        writer = csv.writer(response)
        writer.writerow(["medicine_name", "sku", "barcode", "current_stock", "min_stock_level", "max_stock_level"])
        for item in queryset:
            writer.writerow([
                item.medicine.name,
                item.medicine.sku,
                item.medicine.barcode or "",
                item.current_stock,
                item.min_stock_level,
                item.max_stock_level,
            ])
        pharmacy = None if request.user.is_superuser else require_user_pharmacy(request.user)
        InventoryService.log_activity(
            pharmacy=pharmacy,
            user=request.user,
            action=ActivityLog.ACTION_EXPORT,
            entity_type="Inventory",
            description=_("Inventory exported to CSV"),
        )
        return response

    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"error": _("CSV file is required.")}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_superuser:
            pharmacy_id = request.data.get("pharmacy_id")
            pharmacy = Pharmacy.objects.filter(id=pharmacy_id).first()
            if pharmacy is None:
                return Response({"error": _("pharmacy_id is required for superuser")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            pharmacy = require_user_pharmacy(request.user)

        decoded = upload.read().decode("utf-8-sig").splitlines()
        reader = csv.DictReader(decoded)
        updated = 0
        errors = []
        from apps.medicines.models import Medicine

        for row_number, row in enumerate(reader, start=2):
            try:
                sku = (row.get("sku") or row.get("medicine_sku") or "").strip()
                barcode = (row.get("barcode") or "").strip()
                medicine = None
                if sku:
                    medicine = Medicine.objects.filter(pharmacy=pharmacy, sku=sku).first()
                if medicine is None and barcode:
                    medicine = Medicine.objects.filter(pharmacy=pharmacy, barcode=barcode).first()
                if medicine is None:
                    raise ValueError("Medicine not found by sku/barcode")

                inventory, _created = Inventory.objects.get_or_create(medicine=medicine, pharmacy=pharmacy)
                if row.get("min_stock_level") not in (None, ""):
                    inventory.min_stock_level = int(row["min_stock_level"])
                if row.get("max_stock_level") not in (None, ""):
                    inventory.max_stock_level = int(row["max_stock_level"])
                inventory.save(update_fields=["min_stock_level", "max_stock_level", "updated_at"])

                if row.get("current_stock") not in (None, ""):
                    InventoryService.set_stock(
                        inventory=inventory,
                        new_quantity=int(row["current_stock"]),
                        user=request.user,
                        reason=_("Inventory CSV import"),
                    )
                updated += 1
            except (TypeError, ValueError) as exc:
                errors.append({"row": row_number, "error": str(exc)})

        InventoryService.log_activity(
            pharmacy=pharmacy,
            user=request.user,
            action=ActivityLog.ACTION_IMPORT,
            entity_type="Inventory",
            description=_("Inventory imported from CSV"),
            metadata={"updated": updated, "errors": len(errors)},
        )
        return Response({"updated": updated, "errors": errors}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def reorder_recommendations(self, request):
        if request.user.is_superuser:
            pharmacy_id = request.query_params.get("pharmacy_id")
            if not pharmacy_id:
                return Response(
                    {"error": _("pharmacy_id is required for superuser")},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            pharmacy = Pharmacy.objects.filter(id=pharmacy_id).first()
            if pharmacy is None:
                return Response({"error": _("Pharmacy not found")}, status=status.HTTP_404_NOT_FOUND)
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
            return Response({"error": _("Only pending recommendations can be approved")}, status=status.HTTP_400_BAD_REQUEST)

        recommendation.status = "APPROVED"
        recommendation.approved_by = request.user
        recommendation.approved_at = timezone.now()
        recommendation.save()

        try:
            inventory = Inventory.objects.get(
                medicine=recommendation.medicine,
                pharmacy=recommendation.pharmacy,
            )
            InventoryService.adjust_stock(
                inventory=inventory,
                quantity_change=recommendation.recommended_quantity,
                movement_type=StockMovement.TYPE_PURCHASE,
                user=request.user,
                source_type="ReorderRecommendation",
                source_id=recommendation.id,
                reason=_("Approved reorder recommendation"),
                mark_restocked=True,
            )
        except Inventory.DoesNotExist:
            pass

        serializer = self.get_serializer(recommendation)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        recommendation = self.get_object()
        if recommendation.status != "PENDING":
            return Response({"error": _("Only pending recommendations can be rejected")}, status=status.HTTP_400_BAD_REQUEST)

        recommendation.status = "REJECTED"
        recommendation.save()
        serializer = self.get_serializer(recommendation)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SupplierViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Supplier.objects.select_related("pharmacy").all()
    serializer_class = SupplierSerializer
    permission_classes = [InventoryRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "contact_person", "phone", "email"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_queryset(self):
        return self.get_tenant_queryset(super().get_queryset())

    def perform_create(self, serializer):
        pharmacy = require_user_pharmacy(self.request.user) if not self.request.user.is_superuser else serializer.validated_data.get("pharmacy")
        supplier = serializer.save(pharmacy=pharmacy)
        InventoryService.log_activity(
            pharmacy=pharmacy,
            user=self.request.user,
            action=ActivityLog.ACTION_CREATE,
            entity_type="Supplier",
            entity_id=supplier.id,
            description=f"Supplier created: {supplier.name}",
        )


class PurchaseOrderViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier", "pharmacy", "created_by").prefetch_related("items__medicine").all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [InventoryRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["reference_number", "supplier__name", "notes"]
    ordering_fields = ["ordered_at", "received_at", "total_cost", "status"]
    ordering = ["-ordered_at"]

    def get_queryset(self):
        queryset = self.get_tenant_queryset(super().get_queryset())
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        purchase_order = serializer.save()
        InventoryService.log_activity(
            pharmacy=purchase_order.pharmacy,
            user=self.request.user,
            action=ActivityLog.ACTION_CREATE,
            entity_type="PurchaseOrder",
            entity_id=purchase_order.id,
            description=f"Purchase order created: {purchase_order.reference_number or purchase_order.id}",
            metadata={"supplier_id": purchase_order.supplier_id, "items": purchase_order.items.count()},
        )

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        purchase_order = self.get_object()
        purchase_order = InventoryService.receive_purchase_order(purchase_order, user=request.user)
        serializer = self.get_serializer(purchase_order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StockMovementViewSet(TenantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = StockMovement.objects.select_related("medicine", "inventory", "user", "pharmacy").all()
    serializer_class = StockMovementSerializer
    permission_classes = [InventoryRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["medicine__name", "medicine__sku", "reason", "source_type"]
    ordering_fields = ["created_at", "quantity_change", "movement_type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = self.get_tenant_queryset(super().get_queryset())
        medicine_id = self.request.query_params.get("medicine")
        if medicine_id:
            queryset = queryset.filter(medicine_id=medicine_id)
        movement_type = self.request.query_params.get("movement_type")
        if movement_type:
            queryset = queryset.filter(movement_type=movement_type)
        return queryset


class ActivityLogViewSet(TenantScopedQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.select_related("user", "pharmacy").all()
    serializer_class = ActivityLogSerializer
    permission_classes = [InventoryRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["description", "entity_type", "action"]
    ordering_fields = ["created_at", "action", "entity_type"]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = self.get_tenant_queryset(super().get_queryset())
        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
        return queryset
