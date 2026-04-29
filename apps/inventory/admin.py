"""
Admin configuration for inventory app.
"""
from django.contrib import admin
from .models import ActivityLog, Inventory, PurchaseOrder, PurchaseOrderItem, ReorderRecommendation, StockMovement, Supplier


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    """Admin interface for Inventory model."""
    list_display = ['medicine', 'pharmacy', 'current_stock', 'min_stock_level', 'max_stock_level', 'needs_reorder', 'last_restocked_date']
    # list_filter = ['needs_reorder', 'last_restocked_date', 'created_at']
    search_fields = ['medicine__name', 'medicine__sku', 'pharmacy__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Medicine', {
            'fields': ('pharmacy', 'medicine')
        }),
        ('Stock Levels', {
            'fields': ('current_stock', 'min_stock_level', 'max_stock_level')
        }),
        ('Restock Information', {
            'fields': ('last_restocked_date',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ReorderRecommendation)
class ReorderRecommendationAdmin(admin.ModelAdmin):
    """Admin interface for ReorderRecommendation model."""
    list_display = ['medicine', 'pharmacy', 'recommended_quantity', 'priority', 'status', 'created_at', 'approved_by']
    list_filter = ['pharmacy', 'status', 'priority', 'created_at']
    search_fields = ['medicine__name', 'reason', 'pharmacy__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Medicine Information', {
            'fields': ('pharmacy', 'medicine', 'recommended_quantity')
        }),
        ('Recommendation Details', {
            'fields': ('reason', 'priority', 'status')
        }),
        ('Approval Information', {
            'fields': ('approved_by', 'approved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "pharmacy", "phone", "email", "is_active", "created_at"]
    list_filter = ["pharmacy", "is_active", "created_at"]
    search_fields = ["name", "contact_person", "phone", "email", "pharmacy__name"]


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ["line_total", "created_at"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["id", "reference_number", "pharmacy", "supplier", "status", "total_cost", "ordered_at", "received_at"]
    list_filter = ["pharmacy", "status", "ordered_at"]
    search_fields = ["reference_number", "supplier__name", "pharmacy__name"]
    readonly_fields = ["ordered_at", "received_at", "total_cost", "created_at", "updated_at"]
    inlines = [PurchaseOrderItemInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["medicine", "pharmacy", "movement_type", "quantity_change", "stock_after", "user", "created_at"]
    list_filter = ["pharmacy", "movement_type", "created_at"]
    search_fields = ["medicine__name", "medicine__sku", "reason", "source_type"]
    readonly_fields = ["created_at"]


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "pharmacy", "action", "entity_type", "entity_id", "user", "description"]
    list_filter = ["pharmacy", "action", "entity_type", "created_at"]
    search_fields = ["description", "entity_type", "user__username"]
    readonly_fields = ["created_at"]
