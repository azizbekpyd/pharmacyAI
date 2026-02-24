"""
Admin configuration for inventory app.
"""
from django.contrib import admin
from .models import Inventory, ReorderRecommendation


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
