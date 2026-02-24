"""
Serializers for sales app.

Handles serialization/deserialization of Sale and SaleItem models.
"""
from rest_framework import serializers
from django.db import transaction
from .models import Sale, SaleItem
from apps.medicines.models import Medicine
from apps.inventory.models import Inventory
from apps.tenants.utils import require_user_pharmacy


class SaleItemSerializer(serializers.ModelSerializer):
    """
    Serializer for SaleItem model.
    """
    medicine_name = serializers.CharField(source='medicine.name', read_only=True)
    medicine_sku = serializers.CharField(source='medicine.sku', read_only=True)
    medicine_id = serializers.PrimaryKeyRelatedField(
        queryset=Medicine.objects.all(),
        source='medicine',
        write_only=True
    )
    
    class Meta:
        model = SaleItem
        fields = [
            'id', 'medicine', 'medicine_id', 'medicine_name', 'medicine_sku',
            'quantity', 'unit_price', 'subtotal', 'created_at'
        ]
        read_only_fields = ['id', 'subtotal', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return
        if request.user.is_superuser:
            return

        pharmacy = require_user_pharmacy(request.user)
        self.fields["medicine_id"].queryset = Medicine.objects.filter(pharmacy=pharmacy)


class SaleSerializer(serializers.ModelSerializer):
    """
    Serializer for Sale model.
    """
    items = SaleItemSerializer(many=True, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    pharmacy_name = serializers.CharField(source='pharmacy.name', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'date', 'total_amount', 'user', 'user_name', 'user_username',
            'pharmacy', 'pharmacy_name',
            'notes', 'items', 'items_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'date', 'total_amount', 'created_at', 'updated_at', 'items_count', 'pharmacy_name']
    
    def get_items_count(self, obj):
        """Get count of items in the sale."""
        return obj.items.count()


class SaleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new sale with items.
    
    Handles nested creation of sale items.
    """
    items = SaleItemSerializer(many=True)
    
    class Meta:
        model = Sale
        fields = ['date', 'user', 'pharmacy', 'notes', 'items']
        extra_kwargs = {
            "user": {"required": False},
            "pharmacy": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return
        if request.user.is_superuser:
            return

        pharmacy = require_user_pharmacy(request.user)
        self.fields["items"].child.fields["medicine_id"].queryset = Medicine.objects.filter(pharmacy=pharmacy)
    
    def create(self, validated_data):
        """
        Create sale and associated sale items.
        
        Automatically calculates total_amount from items.
        """
        items_data = validated_data.pop('items')
        request = self.context.get("request")
        user = request.user if request and request.user.is_authenticated else validated_data.get("user")

        if request and request.user.is_authenticated and not request.user.is_superuser:
            pharmacy = require_user_pharmacy(request.user)
            validated_data["pharmacy"] = pharmacy
            validated_data["user"] = request.user
        elif request and request.user.is_authenticated and request.user.is_superuser:
            pharmacy = validated_data.get("pharmacy")
            if pharmacy is None:
                raise serializers.ValidationError({"pharmacy": "Superuser must provide pharmacy."})
            if "user" not in validated_data:
                validated_data["user"] = request.user
        else:
            pharmacy = validated_data.get("pharmacy")
            if pharmacy is None:
                raise serializers.ValidationError({"pharmacy": "Pharmacy is required."})
            if "user" not in validated_data:
                validated_data["user"] = user

        with transaction.atomic():
            sale = Sale.objects.create(**validated_data)

            total_amount = 0
            for item_data in items_data:
                item_data["pharmacy"] = sale.pharmacy
                if item_data["medicine"].pharmacy_id != sale.pharmacy_id:
                    raise serializers.ValidationError(
                        {"items": "Medicine does not belong to sale pharmacy."}
                    )
                item = SaleItem.objects.create(sale=sale, **item_data)
                total_amount += item.subtotal

                # Reduce stock for future sales flow; keep simple and safe.
                inventory, _ = Inventory.objects.get_or_create(
                    medicine=item.medicine,
                    pharmacy=sale.pharmacy,
                    defaults={
                        'current_stock': 0,
                        'min_stock_level': 20,
                        'max_stock_level': 120,
                    }
                )
                inventory.current_stock = max(0, inventory.current_stock - item.quantity)
                inventory.save(update_fields=['current_stock', 'updated_at'])

            sale.total_amount = total_amount
            sale.save()

            return sale


class SaleListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for sale list views.
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    pharmacy_name = serializers.CharField(source='pharmacy.name', read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Sale
        fields = [
            'id', 'date', 'total_amount', 'user_name',
            'pharmacy_name', 'items_count', 'created_at'
        ]
    
    def get_items_count(self, obj):
        """Get count of items in the sale."""
        return obj.items.count()
