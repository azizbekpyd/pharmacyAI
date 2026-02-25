"""
Serializers for POS integration app.

Handles serialization of POS data for ingestion.
"""
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from apps.sales.models import Sale, SaleItem
from apps.medicines.models import Medicine
from apps.tenants.services import SubscriptionService
from apps.tenants.utils import require_user_pharmacy


class POSSaleItemSerializer(serializers.Serializer):
    """
    Serializer for POS sale item data.
    
    Accepts flexible input formats from POS systems.
    """
    medicine_sku = serializers.CharField(help_text="Medicine SKU")
    medicine_name = serializers.CharField(required=False, help_text="Medicine name (optional)")
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    def _get_target_pharmacy(self):
        pharmacy = self.context.get("pharmacy")
        if pharmacy is not None:
            return pharmacy
        user = self.context.get("user")
        if user and user.is_authenticated and not user.is_superuser:
            return require_user_pharmacy(user)
        return None
    
    def validate_medicine_sku(self, value):
        """Validate that medicine with SKU exists."""
        queryset = Medicine.objects.filter(sku=value)
        pharmacy = self._get_target_pharmacy()
        if pharmacy is not None:
            queryset = queryset.filter(pharmacy=pharmacy)
        if not queryset.exists():
            raise serializers.ValidationError(f"Medicine with SKU '{value}' not found.")
        return value


class POSSaleSerializer(serializers.Serializer):
    """
    Serializer for POS sale data.
    
    Accepts sales data from external POS systems.
    """
    sale_id = serializers.CharField(required=False, help_text="External sale ID from POS system")
    date = serializers.DateTimeField(required=False, help_text="Sale date (defaults to now)")
    items = POSSaleItemSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        """Validate that items list is not empty."""
        if not value:
            raise serializers.ValidationError("Sale must have at least one item.")
        return value
    
    def create(self, validated_data):
        """
        Create a sale from POS data.
        
        Handles medicine lookup by SKU and creates sale with items.
        """
        items_data = validated_data.pop('items')
        sale_date = validated_data.get('date')
        user = self.context.get("user")

        pharmacy = self.context.get("pharmacy")
        if pharmacy is None:
            if user and user.is_authenticated and not user.is_superuser:
                pharmacy = require_user_pharmacy(user)
            elif user and user.is_authenticated and user.is_superuser:
                raise serializers.ValidationError({"pharmacy": "Superuser must provide pharmacy context."})

        if not (user and user.is_authenticated and user.is_superuser):
            try:
                SubscriptionService.enforce_limits(pharmacy, SubscriptionService.RESOURCE_MONTHLY_SALES)
            except DjangoValidationError as exc:
                if hasattr(exc, "message_dict"):
                    raise serializers.ValidationError(exc.message_dict)
                raise serializers.ValidationError({"subscription": exc.messages})

        # Create sale
        sale = Sale.objects.create(
            date=sale_date or timezone.now(),
            user=user,
            pharmacy=pharmacy,
            notes=validated_data.get('notes', ''),
            total_amount=0,
        )
        
        total_amount = 0
        
        # Create sale items
        for item_data in items_data:
            try:
                medicine_query = Medicine.objects.filter(sku=item_data['medicine_sku'])
                if pharmacy is not None:
                    medicine_query = medicine_query.filter(pharmacy=pharmacy)
                medicine = medicine_query.get()
                unit_price = item_data.get('unit_price', medicine.unit_price)
                
                sale_item = SaleItem.objects.create(
                    sale=sale,
                    pharmacy=sale.pharmacy,
                    medicine=medicine,
                    quantity=item_data['quantity'],
                    unit_price=unit_price
                )
                
                total_amount += sale_item.subtotal
                
                # Update inventory (subtract sold quantity)
                try:
                    inventory = medicine.inventory
                    inventory.current_stock -= item_data['quantity']
                    if inventory.current_stock < 0:
                        inventory.current_stock = 0
                    inventory.save()
                except:
                    pass  # Inventory might not exist
                    
            except Medicine.DoesNotExist:
                # Skip invalid items or handle error
                continue
        
        # Update sale total
        sale.total_amount = total_amount
        sale.save()
        
        return sale


class POSBulkSaleSerializer(serializers.Serializer):
    """
    Serializer for bulk sale data from POS system.
    
    Accepts multiple sales at once.
    """
    sales = POSSaleSerializer(many=True)
    
    def create(self, validated_data):
        """Create multiple sales from bulk data."""
        sales_data = validated_data['sales']
        created_sales = []
        
        for sale_data in sales_data:
            serializer = POSSaleSerializer(data=sale_data, context=self.context)
            if serializer.is_valid():
                sale = serializer.save()
                created_sales.append(sale)
        
        return created_sales
