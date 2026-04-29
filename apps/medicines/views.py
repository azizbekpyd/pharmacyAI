"""
API views for medicines app.

Handles CRUD operations for medicines and categories, plus expiry alerts
and CSV import/export.
"""
import csv
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.permissions import CategoryRolePermission, MedicineRolePermission
from apps.inventory.models import ActivityLog
from apps.inventory.services import InventoryService
from apps.tenants.mixins import TenantScopedQuerysetMixin
from apps.tenants.utils import require_user_pharmacy
from apps.inventory.models import Inventory
from .models import Category, Medicine
from .serializers import CategorySerializer, MedicineListSerializer, MedicineSerializer


class CategoryViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Category model.

    Provides CRUD operations for medicine categories.
    """

    queryset = Category.objects.select_related("pharmacy").all()
    serializer_class = CategorySerializer
    permission_classes = [CategoryRolePermission]
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
    permission_classes = [MedicineRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sku", "barcode", "description"]
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

        barcode = self.request.query_params.get("barcode")
        if barcode:
            queryset = queryset.filter(barcode=barcode)

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

    @action(detail=False, methods=["get"])
    def export_csv(self, request):
        queryset = self.get_queryset().select_related("category").order_by("name")
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="medicines.csv"'
        writer = csv.writer(response)
        writer.writerow([
            "name",
            "sku",
            "barcode",
            "category",
            "unit_price",
            "cost_price",
            "expiry_date",
            "current_stock",
            "description",
        ])
        for medicine in queryset:
            inventory = getattr(medicine, "inventory", None)
            writer.writerow([
                medicine.name,
                medicine.sku,
                medicine.barcode or "",
                medicine.category.name if medicine.category else "",
                medicine.unit_price,
                medicine.cost_price,
                medicine.expiry_date or "",
                inventory.current_stock if inventory else 0,
                medicine.description or "",
            ])
        pharmacy = None if request.user.is_superuser else require_user_pharmacy(request.user)
        InventoryService.log_activity(
            pharmacy=pharmacy,
            user=request.user,
            action=ActivityLog.ACTION_EXPORT,
            entity_type="Medicine",
            description="Medicines exported to CSV",
        )
        return response

    @action(detail=False, methods=["post"])
    def import_csv(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"error": "CSV file is required."}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.is_superuser:
            pharmacy_id = request.data.get("pharmacy_id")
            from apps.tenants.models import Pharmacy

            pharmacy = Pharmacy.objects.filter(id=pharmacy_id).first()
            if pharmacy is None:
                return Response({"error": "pharmacy_id is required for superuser."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            pharmacy = require_user_pharmacy(request.user)

        decoded = upload.read().decode("utf-8-sig").splitlines()
        reader = csv.DictReader(decoded)
        created = 0
        updated = 0
        errors = []
        with transaction.atomic():
            for row_number, row in enumerate(reader, start=2):
                try:
                    name = (row.get("name") or "").strip()
                    sku = (row.get("sku") or "").strip()
                    if not name or not sku:
                        raise ValueError("name and sku are required")
                    category_name = (row.get("category") or "").strip()
                    category = None
                    if category_name:
                        category, _ = Category.objects.get_or_create(
                            pharmacy=pharmacy,
                            name=category_name,
                            defaults={"description": ""},
                        )
                    unit_price = Decimal(str(row.get("unit_price") or "0"))
                    cost_price = Decimal(str(row.get("cost_price") or "0"))
                    if unit_price <= 0:
                        raise ValueError("unit_price must be greater than 0")
                    medicine, was_created = Medicine.objects.update_or_create(
                        pharmacy=pharmacy,
                        sku=sku,
                        defaults={
                            "name": name,
                            "barcode": (row.get("barcode") or "").strip() or None,
                            "category": category,
                            "unit_price": unit_price,
                            "cost_price": cost_price,
                            "expiry_date": row.get("expiry_date") or None,
                            "description": row.get("description") or "",
                        },
                    )
                    stock_raw = row.get("current_stock")
                    if stock_raw not in (None, ""):
                        inventory, _ = Inventory.objects.get_or_create(medicine=medicine, pharmacy=pharmacy)
                        InventoryService.set_stock(
                            inventory=inventory,
                            new_quantity=int(stock_raw),
                            user=request.user,
                            reason="CSV import",
                        )
                    if was_created:
                        created += 1
                    else:
                        updated += 1
                except (ValueError, InvalidOperation, IntegrityError) as exc:
                    errors.append({"row": row_number, "error": str(exc)})
        InventoryService.log_activity(
            pharmacy=pharmacy,
            user=request.user,
            action=ActivityLog.ACTION_IMPORT,
            entity_type="Medicine",
            description="Medicines imported from CSV",
            metadata={"created": created, "updated": updated, "errors": len(errors)},
        )
        return Response({"created": created, "updated": updated, "errors": errors}, status=status.HTTP_200_OK)
