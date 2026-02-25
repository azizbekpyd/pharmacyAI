"""
User models for Pharmacy Analytic AI.

This module defines the custom User model with role-based access control.
Roles: Admin, Manager, Pharmacist
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    Roles:
    - ADMIN: Full system access
    - MANAGER: Can manage medicines and operations (cannot delete medicines)
    - PHARMACIST: Can view data and create sales
    """
    ROLE_ADMIN = "ADMIN"
    ROLE_MANAGER = "MANAGER"
    ROLE_PHARMACIST = "PHARMACIST"
    LEGACY_ROLE_PHARMACY_MANAGER = "PHARMACY_MANAGER"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_MANAGER, "Manager"),
        (ROLE_PHARMACIST, "Pharmacist"),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_MANAGER,
        help_text="User role determines access level"
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact phone number"
    )
    pharmacy = models.ForeignKey(
        "tenants.Pharmacy",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Pharmacy this user belongs to",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.is_superuser or self.role == self.ROLE_ADMIN
    
    def is_manager(self):
        """Check if user is a manager (including legacy manager value)."""
        return self.role in {self.ROLE_MANAGER, self.LEGACY_ROLE_PHARMACY_MANAGER}

    def is_pharmacy_manager(self):
        """Backward-compatible alias for manager role checks."""
        return self.is_manager()

    def is_pharmacist(self):
        """Check if user is a pharmacist."""
        return self.role == self.ROLE_PHARMACIST

    def can_manage_medicines(self):
        """Admin and manager can create/edit medicines."""
        return self.is_admin() or self.is_manager()

    def can_delete_medicines(self):
        """Only admin can delete medicines."""
        return self.is_admin()

    def can_create_sales(self):
        """All configured roles can create sales."""
        return self.is_admin() or self.is_manager() or self.is_pharmacist()

    def can_manage_inventory(self):
        """Admin and manager can modify inventory/reorder entities."""
        return self.is_admin() or self.is_manager()
