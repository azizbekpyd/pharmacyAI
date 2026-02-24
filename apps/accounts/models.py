"""
User models for Pharmacy Analytic AI.

This module defines the custom User model with role-based access control.
Roles: Admin and PharmacyManager
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    Roles:
    - ADMIN: Full system access
    - PHARMACY_MANAGER: Limited access to manage pharmacy operations
    """
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('PHARMACY_MANAGER', 'Pharmacy Manager'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='PHARMACY_MANAGER',
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
        return self.role == 'ADMIN'
    
    def is_pharmacy_manager(self):
        """Check if user is a pharmacy manager."""
        return self.role == 'PHARMACY_MANAGER'
