"""
Inventory models for Pharmacy Analytic AI.

This module defines models for inventory tracking and reorder recommendations.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator
from apps.medicines.models import Medicine


class Inventory(models.Model):
    """
    Inventory model tracking stock levels for each medicine.
    
    This model maintains current stock, minimum/maximum levels, and restock history.
    """
    medicine = models.OneToOneField(
        Medicine,
        on_delete=models.CASCADE,
        related_name='inventory',
        help_text="Medicine this inventory record belongs to"
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="inventories",
        help_text="Pharmacy that owns this inventory record",
    )
    current_stock = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Current quantity in stock"
    )
    min_stock_level = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text="Minimum stock level before reorder is recommended"
    )
    max_stock_level = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Maximum stock level (target restock amount)"
    )
    last_restocked_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when inventory was last restocked"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Inventory"
        verbose_name_plural = "Inventories"
        ordering = ['medicine__name']
        indexes = [
            models.Index(fields=['current_stock']),
        ]
    
    def __str__(self):
        return f"{self.medicine.name} - Stock: {self.current_stock}"

    def clean(self):
        super().clean()
        if self.medicine_id and self.pharmacy_id and self.medicine.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"medicine": "Medicine must belong to the same pharmacy."})
    
    def needs_reorder(self):
        """
        Check if inventory needs reordering.
        
        Returns:
            bool: True if current_stock < min_stock_level
        """
        return self.current_stock < self.min_stock_level
    
    def get_reorder_quantity(self):
        """
        Calculate recommended reorder quantity.
        
        Returns:
            int: Recommended quantity to order (max_stock_level - current_stock)
        """
        if self.current_stock < self.max_stock_level:
            return self.max_stock_level - self.current_stock
        return 0
    
    def stock_percentage(self):
        """
        Calculate stock level as percentage of max_stock_level.
        
        Returns:
            float: Percentage (0-100)
        """
        if self.max_stock_level == 0:
            return 0
        return (self.current_stock / self.max_stock_level) * 100


class ReorderRecommendation(models.Model):
    """
    Reorder recommendation model.
    
    System-generated recommendations for medicines that need restocking.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FULFILLED', 'Fulfilled'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]
    
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='reorder_recommendations',
        help_text="Medicine that needs reordering"
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="reorder_recommendations",
        help_text="Pharmacy that owns this recommendation",
    )
    recommended_quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Recommended quantity to order"
    )
    reason = models.TextField(
        help_text="Reason for the recommendation (e.g., Low stock, High demand)"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM',
        help_text="Priority level of the recommendation"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text="Status of the recommendation"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reorders',
        help_text="User who approved the recommendation"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Reorder Recommendation"
        verbose_name_plural = "Reorder Recommendations"
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Reorder {self.medicine.name} - {self.recommended_quantity} units ({self.get_priority_display()})"

    def clean(self):
        super().clean()
        if self.medicine_id and self.pharmacy_id and self.medicine.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"medicine": "Medicine must belong to the same pharmacy."})
