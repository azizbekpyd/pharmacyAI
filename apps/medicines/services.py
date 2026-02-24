from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.inventory.models import Inventory

from .models import Medicine


class MedicineService:
    @staticmethod
    def create_medicine_with_inventory(*, pharmacy, medicine_data, initial_stock=0):
        """
        Create medicine and one-to-one inventory atomically for a tenant.
        """
        if pharmacy is None:
            raise ValidationError({"pharmacy": "Pharmacy is required."})

        try:
            initial_stock = int(initial_stock or 0)
        except (TypeError, ValueError):
            raise ValidationError({"initial_stock": "Initial stock must be an integer."})

        if initial_stock < 0:
            raise ValidationError({"initial_stock": "Initial stock must be non-negative."})

        category = medicine_data.get("category")
        if category is not None and category.pharmacy_id != pharmacy.id:
            raise ValidationError({"category": "Category must belong to the same pharmacy."})

        unit_price = medicine_data.get("unit_price")
        if unit_price is not None and not isinstance(unit_price, Decimal):
            try:
                medicine_data["unit_price"] = Decimal(str(unit_price))
            except (InvalidOperation, TypeError, ValueError):
                raise ValidationError({"unit_price": "Unit price is invalid."})

        with transaction.atomic():
            medicine = Medicine.objects.create(
                pharmacy=pharmacy,
                **medicine_data,
            )
            inventory, created = Inventory.objects.get_or_create(
                medicine=medicine,
                defaults={
                    "pharmacy": pharmacy,
                    "current_stock": initial_stock,
                },
            )
            if not created:
                inventory.pharmacy = pharmacy
                inventory.current_stock = initial_stock
                inventory.save(update_fields=["pharmacy", "current_stock", "updated_at"])

        return medicine

