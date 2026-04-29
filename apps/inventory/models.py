"""
Inventory models for Pharmacy Analytic AI.

This module defines models for inventory tracking, purchases, stock movement
ledger entries, activity logs, and reorder recommendations.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
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
        help_text=_("Medicine this inventory record belongs to"),
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="inventories",
        help_text=_("Pharmacy that owns this inventory record"),
    )
    current_stock = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Current quantity in stock"),
    )
    min_stock_level = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1)],
        help_text=_("Minimum stock level before reorder is recommended"),
    )
    max_stock_level = models.PositiveIntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text=_("Maximum stock level (target restock amount)"),
    )
    last_restocked_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date when inventory was last restocked"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Inventory")
        verbose_name_plural = _("Inventories")
        ordering = ['medicine__name']
        indexes = [
            models.Index(fields=['current_stock']),
        ]
    
    def __str__(self):
        return f"{self.medicine.name} - Stock: {self.current_stock}"

    def clean(self):
        super().clean()
        if self.medicine_id and self.pharmacy_id and self.medicine.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"medicine": _("Medicine must belong to the same pharmacy.")})
    
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
        ('PENDING', _("Pending")),
        ('APPROVED', _("Approved")),
        ('REJECTED', _("Rejected")),
        ('FULFILLED', _("Fulfilled")),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', _("Low")),
        ('MEDIUM', _("Medium")),
        ('HIGH', _("High")),
        ('URGENT', _("Urgent")),
    ]
    
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.CASCADE,
        related_name='reorder_recommendations',
        help_text=_("Medicine that needs reordering"),
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="reorder_recommendations",
        help_text=_("Pharmacy that owns this recommendation"),
    )
    recommended_quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text=_("Recommended quantity to order"),
    )
    reason = models.TextField(
        help_text=_("Reason for the recommendation (e.g., Low stock, High demand)"),
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM',
        help_text=_("Priority level of the recommendation"),
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING',
        help_text=_("Status of the recommendation"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reorders',
        help_text=_("User who approved the recommendation"),
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _("Reorder Recommendation")
        verbose_name_plural = _("Reorder Recommendations")
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
            raise ValidationError({"medicine": _("Medicine must belong to the same pharmacy.")})


class Supplier(models.Model):
    """Supplier/contact used by a pharmacy purchase workflow."""

    name = models.CharField(max_length=200)
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="suppliers",
    )
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["pharmacy", "name"], name="uniq_supplier_pharmacy_name"),
        ]
        indexes = [
            models.Index(fields=["pharmacy", "name"]),
        ]

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """Incoming stock purchase from a supplier."""

    STATUS_DRAFT = "DRAFT"
    STATUS_RECEIVED = "RECEIVED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, _("Draft")),
        (STATUS_RECEIVED, _("Received")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    reference_number = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    ordered_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_purchase_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-ordered_at"]
        indexes = [
            models.Index(fields=["pharmacy", "status"]),
            models.Index(fields=["ordered_at"]),
        ]

    def __str__(self):
        label = self.reference_number or self.pk
        return f"Purchase #{label} - {self.supplier.name}"

    def recalculate_total(self):
        total = sum((item.line_total for item in self.items.all()), Decimal("0.00"))
        self.total_cost = total
        return total

    def clean(self):
        super().clean()
        if self.supplier_id and self.pharmacy_id and self.supplier.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"supplier": _("Supplier must belong to the same pharmacy.")})


class PurchaseOrderItem(models.Model):
    """Medicine line inside a purchase order."""

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="purchase_order_items",
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="purchase_items",
    )
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=80, blank=True)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["medicine__name"]
        indexes = [
            models.Index(fields=["pharmacy", "medicine"]),
        ]

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity}"

    def clean(self):
        super().clean()
        if self.purchase_order_id and self.pharmacy_id and self.purchase_order.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"purchase_order": _("Purchase order must belong to the same pharmacy.")})
        if self.medicine_id and self.pharmacy_id and self.medicine.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"medicine": _("Medicine must belong to the same pharmacy.")})

    def save(self, *args, **kwargs):
        if self.purchase_order_id and self.pharmacy_id is None:
            self.pharmacy_id = self.purchase_order.pharmacy_id
        self.line_total = self.quantity * self.unit_cost
        super().save(*args, **kwargs)


class StockMovement(models.Model):
    """Append-only stock ledger entry for every inventory-changing event."""

    TYPE_PURCHASE = "PURCHASE"
    TYPE_SALE = "SALE"
    TYPE_ADJUSTMENT = "ADJUSTMENT"
    TYPE_RETURN = "RETURN"
    TYPE_EXPIRED_REMOVAL = "EXPIRED_REMOVAL"
    TYPE_CORRECTION = "CORRECTION"
    MOVEMENT_TYPE_CHOICES = [
        (TYPE_PURCHASE, _("Purchase")),
        (TYPE_SALE, _("Sale")),
        (TYPE_ADJUSTMENT, _("Adjustment")),
        (TYPE_RETURN, _("Return")),
        (TYPE_EXPIRED_REMOVAL, _("Expired removal")),
        (TYPE_CORRECTION, _("Correction")),
    ]

    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="stock_movements",
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        related_name="stock_movements",
    )
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPE_CHOICES)
    quantity_change = models.IntegerField(help_text=_("Signed stock delta. Sales and removals are negative."))
    stock_after = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    source_type = models.CharField(max_length=80, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["pharmacy", "created_at"]),
            models.Index(fields=["medicine", "created_at"]),
            models.Index(fields=["movement_type"]),
        ]

    def __str__(self):
        return f"{self.medicine.name}: {self.quantity_change:+d}"

    def clean(self):
        super().clean()
        if self.inventory_id and self.pharmacy_id and self.inventory.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"inventory": _("Inventory must belong to the same pharmacy.")})
        if self.medicine_id and self.pharmacy_id and self.medicine.pharmacy_id != self.pharmacy_id:
            raise ValidationError({"medicine": _("Medicine must belong to the same pharmacy.")})


class ActivityLog(models.Model):
    """Human-readable audit trail for important workspace actions."""

    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_SALE = "SALE"
    ACTION_STOCK = "STOCK"
    ACTION_PURCHASE = "PURCHASE"
    ACTION_EXPORT = "EXPORT"
    ACTION_IMPORT = "IMPORT"
    ACTION_CHOICES = [
        (ACTION_CREATE, _("Create")),
        (ACTION_UPDATE, _("Update")),
        (ACTION_DELETE, _("Delete")),
        (ACTION_SALE, _("Sale")),
        (ACTION_STOCK, _("Stock")),
        (ACTION_PURCHASE, _("Purchase")),
        (ACTION_EXPORT, _("Export")),
        (ACTION_IMPORT, _("Import")),
    ]

    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.CASCADE,
        related_name="activity_logs",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity_type = models.CharField(max_length=80)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["pharmacy", "created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.get_action_display()} {self.entity_type}: {self.description}"
