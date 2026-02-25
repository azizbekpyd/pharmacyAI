from django.contrib import admin

from .models import Pharmacy


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "owner",
        "plan_type",
        "is_active",
        "subscription_start",
        "subscription_end",
        "max_users",
        "max_medicines",
        "max_monthly_sales",
        "created_at",
    ]
    list_filter = ["plan_type", "is_active", "created_at", "subscription_start", "subscription_end"]
    search_fields = ["name", "owner__username", "owner__email"]
