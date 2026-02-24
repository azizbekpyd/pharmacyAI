"""
Admin configuration for accounts app.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin interface for User model."""
    list_display = ['username', 'email', 'role', 'pharmacy', 'is_active', 'created_at']
    list_filter = ['role', 'pharmacy', 'is_active', 'is_staff', 'created_at']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Information', {'fields': ('role', 'phone_number', 'pharmacy')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Information', {'fields': ('role', 'phone_number', 'pharmacy')}),
    )
