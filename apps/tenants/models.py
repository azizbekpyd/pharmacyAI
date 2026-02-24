from django.conf import settings
from django.db import models


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

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"
