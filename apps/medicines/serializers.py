"""
Serializers for medicines app.

Handles serialization/deserialization of Category and Medicine models.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Category, Medicine
from .services import MedicineService
from apps.tenants.utils import require_user_pharmacy


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer for Category model.
    """
    medicines_count = serializers.SerializerMethodField()
    pharmacy_name = serializers.CharField(source="pharmacy.name", read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'pharmacy', 'pharmacy_name', 'medicines_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'medicines_count', 'pharmacy', 'pharmacy_name']
    
    def get_medicines_count(self, obj):
        """Get count of medicines in this category."""
        return obj.medicines.count()


class MedicineSerializer(serializers.ModelSerializer):
    """
    Serializer for Medicine model.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True
    )
    pharmacy_name = serializers.CharField(source="pharmacy.name", read_only=True)
    initial_stock = serializers.IntegerField(
        write_only=True,
        required=False,
        min_value=0,
        default=0,
        help_text="Initial stock to create Inventory.current_stock.",
    )
    is_expiring_soon = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    current_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Medicine
        fields = [
            'id', 'name', 'category', 'category_id', 'category_name',
            'sku', 'description', 'unit_price', 'expiry_date', 'pharmacy', 'pharmacy_name',
            'initial_stock',
            'is_expiring_soon', 'is_expired', 'current_stock',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_expiring_soon', 'is_expired', 'current_stock', 'pharmacy', 'pharmacy_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return
        if request.user.is_superuser:
            return

        pharmacy = require_user_pharmacy(request.user)
        self.fields["category_id"].queryset = Category.objects.filter(pharmacy=pharmacy)

    def create(self, validated_data):
        """
        Create medicine and initialize inventory atomically.
        """
        initial_stock = validated_data.pop("initial_stock", 0)
        request = self.context.get("request")
        skip_limits = bool(request and request.user and request.user.is_authenticated and request.user.is_superuser)
        pharmacy = validated_data.pop("pharmacy", None)
        if pharmacy is None:
            pharmacy_id = validated_data.pop("pharmacy_id", None)
            if pharmacy_id is not None:
                from apps.tenants.models import Pharmacy

                pharmacy = Pharmacy.objects.filter(id=pharmacy_id).first()
        try:
            return MedicineService.create_medicine_with_inventory(
                pharmacy=pharmacy,
                medicine_data=validated_data,
                initial_stock=initial_stock,
                enforce_limits=not skip_limits,
            )
        except DjangoValidationError as exc:
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict)
            raise serializers.ValidationError({"detail": exc.messages})
    
    def get_is_expiring_soon(self, obj):
        """Check if medicine is expiring within 30 days."""
        return obj.is_expiring_soon()
    
    def get_is_expired(self, obj):
        """Check if medicine has expired."""
        return obj.is_expired()
    
    def get_current_stock(self, obj):
        """Get current stock from inventory."""
        try:
            return obj.inventory.current_stock
        except:
            return 0


class MedicineListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for medicine list views.
    
    Used for better performance in list endpoints.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_expiring_soon = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    is_low_stock = serializers.SerializerMethodField()
    current_stock = serializers.SerializerMethodField()
    pharmacy_name = serializers.CharField(source="pharmacy.name", read_only=True)
    
    class Meta:
        model = Medicine
        fields = [
            'id', 'name', 'category_name', 'sku', 'unit_price',
            'expiry_date', 'is_expiring_soon', 'is_expired', 'is_low_stock', 'current_stock', 'pharmacy_name'
        ]
    
    def get_is_expiring_soon(self, obj):
        """Check if medicine is expiring within 30 days."""
        return obj.is_expiring_soon()
    
    def get_current_stock(self, obj):
        """Get current stock from inventory."""
        try:
            return obj.inventory.current_stock
        except:
            return 0

    def get_is_expired(self, obj):
        """Check if medicine has expired."""
        return obj.is_expired()

    def get_is_low_stock(self, obj):
        """Check if current stock is below minimum stock level."""
        try:
            return obj.inventory.current_stock < obj.inventory.min_stock_level
        except:
            return False
