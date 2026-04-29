"""
Serializers for inventory app.

Handles serialization/deserialization of Inventory and ReorderRecommendation models.
"""
from rest_framework import serializers
from .models import (
    ActivityLog,
    Inventory,
    PurchaseOrder,
    PurchaseOrderItem,
    ReorderRecommendation,
    StockMovement,
    Supplier,
)
from apps.medicines.models import Medicine
from apps.tenants.utils import require_user_pharmacy


class InventorySerializer(serializers.ModelSerializer):
    """
    Serializer for Inventory model.
    """
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_sku = serializers.CharField(source='medicine.sku', read_only=True)
    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.all(),
        source='medicine',
        write_only=True
    )
    pharmacy_name = serializers.CharField(source="pharmacy.name", read_only=True)
    needs_reorder = serializers.SerializerMethodField()
    stock_percentage = serializers.SerializerMethodField()
    recommended_reorder_quantity = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'medicine', 'medicine_id', 'medicine_name', 'medicine_sku',
            'pharmacy', 'pharmacy_name',
            'current_stock', 'min_stock_level', 'max_stock_level',
            'needs_reorder', 'stock_percentage', 'recommended_reorder_quantity',
            'last_restocked_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'needs_reorder', 'stock_percentage',
            'recommended_reorder_quantity', 'pharmacy', 'pharmacy_name'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return
        if request.user.is_superuser:
            return

        pharmacy = require_user_pharmacy(request.user)
        self.fields["medicine_id"].queryset = Medicine.objects.filter(pharmacy=pharmacy)
    
    def get_needs_reorder(self, obj):
        """Check if inventory needs reordering."""
        return obj.needs_reorder()
    
    def get_stock_percentage(self, obj):
        """Get stock level as percentage."""
        return round(obj.stock_percentage(), 2)
    
    def get_recommended_reorder_quantity(self, obj):
        """Get recommended reorder quantity."""
        return obj.get_reorder_quantity()


class InventoryListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for inventory list views.
    """
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_sku = serializers.CharField(source='medicine.sku', read_only=True)
    needs_reorder = serializers.SerializerMethodField()
    stock_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = Inventory
        fields = [
            'id', 'medicine_name', 'medicine_sku',
            'current_stock', 'min_stock_level', 'max_stock_level',
            'needs_reorder', 'stock_percentage'
        ]
    
    def get_needs_reorder(self, obj):
        """Check if inventory needs reordering."""
        return obj.needs_reorder()
    
    def get_stock_percentage(self, obj):
        """Get stock level as percentage."""
        return round(obj.stock_percentage(), 2)


class ReorderRecommendationSerializer(serializers.ModelSerializer):
    """
    Serializer for ReorderRecommendation model.
    """
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_sku = serializers.CharField(source='medicine.sku', read_only=True)
    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.all(),
        source='medicine',
        write_only=True
    )
    pharmacy_name = serializers.CharField(source="pharmacy.name", read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = ReorderRecommendation
        fields = [
            'id', 'medicine', 'medicine_id', 'medicine_name', 'medicine_sku',
            'pharmacy', 'pharmacy_name',
            'recommended_quantity', 'reason', 'priority', 'priority_display',
            'status', 'status_display', 'approved_by', 'approved_by_name',
            'approved_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'approved_by_name', 'pharmacy', 'pharmacy_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return
        if request.user.is_superuser:
            return

        pharmacy = require_user_pharmacy(request.user)
        self.fields["medicine_id"].queryset = Medicine.objects.filter(pharmacy=pharmacy)


class ReorderRecommendationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating reorder recommendations.
    """
    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.all(),
        source='medicine'
    )
    
    class Meta:
        model = ReorderRecommendation
        fields = ['medicine_id', 'recommended_quantity', 'reason', 'priority']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return
        if request.user.is_superuser:
            return

        pharmacy = require_user_pharmacy(request.user)
        self.fields["medicine_id"].queryset = Medicine.objects.filter(pharmacy=pharmacy)


class SupplierSerializer(serializers.ModelSerializer):
    pharmacy_name = serializers.CharField(source="pharmacy.name", read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id",
            "name",
            "pharmacy",
            "pharmacy_name",
            "contact_person",
            "phone",
            "email",
            "address",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "pharmacy", "pharmacy_name", "created_at", "updated_at"]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    medicine_id = serializers.PrimaryKeyRelatedField(queryset=Medicine.objects.all(), source="medicine")
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    medicine_sku = serializers.CharField(source="medicine.sku", read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id",
            "medicine_id",
            "medicine_name",
            "medicine_sku",
            "quantity",
            "unit_cost",
            "expiry_date",
            "batch_number",
            "line_total",
            "created_at",
        ]
        read_only_fields = ["id", "line_total", "created_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or request.user.is_superuser:
            return
        pharmacy = require_user_pharmacy(request.user)
        self.fields["medicine_id"].queryset = Medicine.objects.filter(pharmacy=pharmacy)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    items = PurchaseOrderItemSerializer(many=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "pharmacy",
            "supplier",
            "supplier_name",
            "reference_number",
            "status",
            "ordered_at",
            "received_at",
            "total_cost",
            "notes",
            "created_by",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "pharmacy",
            "status",
            "ordered_at",
            "received_at",
            "total_cost",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated or request.user.is_superuser:
            return
        pharmacy = require_user_pharmacy(request.user)
        self.fields["supplier"].queryset = Supplier.objects.filter(pharmacy=pharmacy, is_active=True)

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        request = self.context.get("request")
        if request and request.user.is_authenticated and not request.user.is_superuser:
            pharmacy = require_user_pharmacy(request.user)
        else:
            pharmacy = validated_data.get("pharmacy")
            if pharmacy is None:
                raise serializers.ValidationError({"pharmacy": "Pharmacy is required."})

        supplier = validated_data["supplier"]
        if supplier.pharmacy_id != pharmacy.id:
            raise serializers.ValidationError({"supplier": "Supplier does not belong to this pharmacy."})

        purchase_order = PurchaseOrder.objects.create(
            pharmacy=pharmacy,
            created_by=request.user if request and request.user.is_authenticated else None,
            **validated_data,
        )
        total = 0
        for item_data in items_data:
            medicine = item_data["medicine"]
            if medicine.pharmacy_id != pharmacy.id:
                raise serializers.ValidationError({"items": "Medicine does not belong to this pharmacy."})
            item = PurchaseOrderItem.objects.create(
                purchase_order=purchase_order,
                pharmacy=pharmacy,
                **item_data,
            )
            total += item.line_total
        purchase_order.total_cost = total
        purchase_order.save(update_fields=["total_cost", "updated_at"])
        return purchase_order


class StockMovementSerializer(serializers.ModelSerializer):
    medicine_name = serializers.CharField(source="medicine.name", read_only=True)
    medicine_sku = serializers.CharField(source="medicine.sku", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)
    movement_type_display = serializers.CharField(source="get_movement_type_display", read_only=True)

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "medicine",
            "medicine_name",
            "medicine_sku",
            "movement_type",
            "movement_type_display",
            "quantity_change",
            "stock_after",
            "unit_cost",
            "source_type",
            "source_id",
            "reason",
            "user",
            "user_name",
            "created_at",
        ]
        read_only_fields = fields


class ActivityLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)

    class Meta:
        model = ActivityLog
        fields = [
            "id",
            "action",
            "action_display",
            "entity_type",
            "entity_id",
            "description",
            "metadata",
            "user",
            "user_name",
            "created_at",
        ]
        read_only_fields = fields
