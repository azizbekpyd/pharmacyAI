from django.contrib import admin

from .models import Pharmacy


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "owner", "plan_type", "created_at"]
    list_filter = ["plan_type", "created_at"]
    search_fields = ["name", "owner__username", "owner__email"]

