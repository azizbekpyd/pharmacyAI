"""
Admin configuration for sales app.
"""
from django.contrib import admin
from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    """Inline admin for SaleItem model."""
    model = SaleItem
    extra = 1
    readonly_fields = ['subtotal', 'created_at', 'pharmacy']


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    """Admin interface for Sale model."""
    list_display = ['id', 'date', 'pharmacy', 'user', 'total_amount', 'created_at']
    list_filter = ['pharmacy', 'date', 'user', 'created_at']
    search_fields = ['id', 'user__username', 'notes', 'pharmacy__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [SaleItemInline]
    date_hierarchy = 'date'


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    """Admin interface for SaleItem model."""
    list_display = ['id', 'sale', 'pharmacy', 'medicine', 'quantity', 'unit_price', 'subtotal', 'created_at']
    list_filter = ['pharmacy', 'created_at', 'medicine__category']
    search_fields = ['medicine__name', 'sale__id', 'pharmacy__name']
    readonly_fields = ['subtotal', 'created_at']
