"""
Serializers for inventory app.

Handles serialization/deserialization of Inventory and ReorderRecommendation models.
"""
from rest_framework import serializers
from .models import Inventory, ReorderRecommendation
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
