"""
Sales models for Pharmacy Analytic AI.

This module defines models for sales records and sale items.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator
from apps.accounts.models import User
from apps.medicines.models import Medicine


class Sale(models.Model):
    """
    Sale model representing a complete sales transaction.
    
    Each sale can contain multiple sale items (medicines).
    """
    date = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time of the sale"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total amount of the sale"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sales',
        help_text="User who processed the sale (cashier)"
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="sales",
        help_text="Pharmacy where the sale was recorded",
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Optional notes about the sale"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sale"
        verbose_name_plural = "Sales"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Sale #{self.id} - {self.date.strftime('%Y-%m-%d %H:%M')} - {self.total_amount} UZS"
    
    def calculate_total(self):
        """
        Calculate total amount from sale items.
        
        Returns:
            Decimal: Total amount of all sale items
        """
        return sum(item.subtotal for item in self.items.all())


class SaleItem(models.Model):
    """
    Sale item model representing individual medicine sold in a sale.
    
    Each sale can have multiple sale items (one medicine per item).
    """
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Parent sale transaction"
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="sale_items",
        help_text="Pharmacy where this item was sold",
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name='sale_items',
        help_text="Medicine that was sold"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity of medicine sold"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per unit at the time of sale"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Subtotal (quantity × unit_price)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Sale Item"
        verbose_name_plural = "Sale Items"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sale']),
            models.Index(fields=['medicine']),
        ]
    
    def __str__(self):
        return f"{self.medicine.name} x{self.quantity} - {self.subtotal} UZS"

    def clean(self):
        super().clean()
        if self.sale_id and self.pharmacy_id and self.sale.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"sale": "Sale must belong to the same pharmacy."})
        if self.medicine_id and self.pharmacy_id and self.medicine.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"medicine": "Medicine must belong to the same pharmacy."})
    
    def save(self, *args, **kwargs):
        """Override save to automatically calculate subtotal."""
        if self.sale_id and self.pharmacy_id is None:
            self.pharmacy_id = self.sale.pharmacy_id
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)
