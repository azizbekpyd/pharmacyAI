"""
Medicine models for Pharmacy Analytic AI.

This module defines models for medicine categories and individual medicines.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator


class Category(models.Model):
    """
    Medicine category model.
    
    Categories help organize medicines (e.g., Antibiotics, Pain Relief, Vitamins).
    """
    name = models.CharField(
        max_length=100,
        help_text="Category name (e.g., Antibiotics, Pain Relief)"
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="categories",
        help_text="Pharmacy that owns this category",
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the category"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=["pharmacy", "name"],
                name="uniq_category_pharmacy_name",
            ),
        ]
    
    def __str__(self):
        return self.name


class Medicine(models.Model):
    """
    Medicine model.
    
    Stores information about each medicine including name, category, price, and expiry date.
    """
    name = models.CharField(
        max_length=200,
        help_text="Medicine name (e.g., Paracetamol 500mg)"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='medicines',
        help_text="Medicine category"
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="medicines",
        help_text="Pharmacy that owns this medicine",
    )
    sku = models.CharField(
        max_length=50,
        help_text="Stock Keeping Unit - unique identifier for the medicine"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of the medicine"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Price per unit"
    )
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Expiry date of the medicine batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Medicine"
        verbose_name_plural = "Medicines"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=["pharmacy", "sku"],
                name="uniq_medicine_pharmacy_sku",
            ),
        ]
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['category']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.sku})"

    def clean(self):
        super().clean()
        if self.category_id and self.pharmacy_id and self.category.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"category": "Category must belong to the same pharmacy."})
    
    def is_expiring_soon(self, days=30):
        """
        Check if medicine is expiring within specified days.
        
        Args:
            days: Number of days to check ahead (default: 30)
        
        Returns:
            bool: True if expiring soon, False otherwise
        """
        if not self.expiry_date:
            return False
        from django.utils import timezone
        from datetime import timedelta
        threshold = timezone.now().date() + timedelta(days=days)
        return self.expiry_date <= threshold
    
    def is_expired(self):
        """Check if medicine has expired."""
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
