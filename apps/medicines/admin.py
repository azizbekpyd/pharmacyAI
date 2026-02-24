"""
Admin configuration for medicines app.
"""
from django.contrib import admin
from .models import Category, Medicine


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin interface for Category model."""
    list_display = ['name', 'pharmacy', 'description', 'created_at']
    search_fields = ['name', 'description', 'pharmacy__name']
    list_filter = ['pharmacy', 'created_at']


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    """Admin interface for Medicine model."""
    list_display = ['name', 'pharmacy', 'sku', 'category', 'unit_price', 'expiry_date', 'is_expired', 'created_at']
    list_filter = ['pharmacy', 'category', 'expiry_date', 'created_at']
    search_fields = ['name', 'sku', 'description', 'pharmacy__name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('pharmacy', 'name', 'sku', 'category', 'description')
        }),
        ('Pricing & Expiry', {
            'fields': ('unit_price', 'expiry_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
