from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta


class Pharmacy(models.Model):
    class PlanType(models.TextChoices):
        BASIC = "BASIC", "Basic"
        PRO = "PRO", "Pro"
        ENTERPRISE = "ENTERPRISE", "Enterprise"

    name = models.CharField(max_length=255)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_pharmacies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    plan_type = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.BASIC,
    )
    subscription_start = models.DateTimeField(null=True, blank=True)
    subscription_end = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    max_users = models.IntegerField(null=True, blank=True)
    max_medicines = models.IntegerField(null=True, blank=True)
    max_monthly_sales = models.IntegerField(null=True, blank=True)

    PLAN_LIMITS = {
        PlanType.BASIC: {"max_users": 3, "max_medicines": 200, "max_monthly_sales": 1000},
        PlanType.PRO: {"max_users": 10, "max_medicines": 2000, "max_monthly_sales": 10000},
        PlanType.ENTERPRISE: {"max_users": None, "max_medicines": None, "max_monthly_sales": None},
    }

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"

    def apply_plan_limits(self):
        limits = self.PLAN_LIMITS.get(self.plan_type, self.PLAN_LIMITS[self.PlanType.BASIC])
        self.max_users = limits["max_users"]
        self.max_medicines = limits["max_medicines"]
        self.max_monthly_sales = limits["max_monthly_sales"]

    def save(self, *args, **kwargs):
        auto_updated_fields = set()
        if self.subscription_start is None:
            self.subscription_start = timezone.now()
            auto_updated_fields.add("subscription_start")
        if self.subscription_end is None:
            self.subscription_end = self.subscription_start + timedelta(days=30)
            auto_updated_fields.add("subscription_end")

        if self.max_users is None and self.plan_type != self.PlanType.ENTERPRISE:
            self.apply_plan_limits()
            auto_updated_fields.update({"max_users", "max_medicines", "max_monthly_sales"})
        elif self.max_medicines is None and self.plan_type != self.PlanType.ENTERPRISE:
            self.apply_plan_limits()
            auto_updated_fields.update({"max_users", "max_medicines", "max_monthly_sales"})
        elif self.max_monthly_sales is None and self.plan_type != self.PlanType.ENTERPRISE:
            self.apply_plan_limits()
            auto_updated_fields.update({"max_users", "max_medicines", "max_monthly_sales"})
        elif self.plan_type == self.PlanType.ENTERPRISE:
            self.apply_plan_limits()
            auto_updated_fields.update({"max_users", "max_medicines", "max_monthly_sales"})

        update_fields = kwargs.get("update_fields")
        if update_fields is not None and auto_updated_fields:
            kwargs["update_fields"] = set(update_fields).union(auto_updated_fields)

        super().save(*args, **kwargs)
