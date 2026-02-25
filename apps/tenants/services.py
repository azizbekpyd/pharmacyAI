from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone


class SubscriptionService:
    RESOURCE_USERS = "users"
    RESOURCE_MEDICINES = "medicines"
    RESOURCE_MONTHLY_SALES = "monthly_sales"
    VALID_RESOURCES = {RESOURCE_USERS, RESOURCE_MEDICINES, RESOURCE_MONTHLY_SALES}

    PLAN_LIMITS = {
        "BASIC": {"max_users": 3, "max_medicines": 200, "max_monthly_sales": 1000},
        "PRO": {"max_users": 10, "max_medicines": 2000, "max_monthly_sales": 10000},
        "ENTERPRISE": {"max_users": None, "max_medicines": None, "max_monthly_sales": None},
    }

    RESOURCE_TO_FIELD = {
        RESOURCE_USERS: "max_users",
        RESOURCE_MEDICINES: "max_medicines",
        RESOURCE_MONTHLY_SALES: "max_monthly_sales",
    }

    RESOURCE_LABELS = {
        RESOURCE_USERS: "users",
        RESOURCE_MEDICINES: "medicines",
        RESOURCE_MONTHLY_SALES: "monthly sales",
    }

    @staticmethod
    def is_subscription_active(pharmacy):
        if pharmacy is None:
            return False
        if not pharmacy.is_active:
            return False
        if pharmacy.subscription_end and timezone.now() > pharmacy.subscription_end:
            return False
        return True

    @staticmethod
    def days_remaining(pharmacy):
        if pharmacy is None or pharmacy.subscription_end is None:
            return None
        return (pharmacy.subscription_end - timezone.now()).days

    @staticmethod
    def _current_usage(pharmacy, resource_type):
        if resource_type == SubscriptionService.RESOURCE_USERS:
            return pharmacy.users.count()
        if resource_type == SubscriptionService.RESOURCE_MEDICINES:
            from apps.medicines.models import Medicine

            return Medicine.objects.filter(pharmacy=pharmacy).count()
        if resource_type == SubscriptionService.RESOURCE_MONTHLY_SALES:
            from apps.sales.models import Sale

            now = timezone.now()
            return Sale.objects.filter(pharmacy=pharmacy, date__year=now.year, date__month=now.month).count()
        raise ValidationError({"resource_type": "Invalid resource type."})

    @staticmethod
    def check_limit(pharmacy, resource_type):
        if resource_type not in SubscriptionService.VALID_RESOURCES:
            raise ValidationError({"resource_type": "Invalid resource type."})
        if pharmacy is None:
            raise ValidationError({"pharmacy": "Pharmacy is required."})

        field_name = SubscriptionService.RESOURCE_TO_FIELD[resource_type]
        limit = getattr(pharmacy, field_name, None)
        used = SubscriptionService._current_usage(pharmacy, resource_type)

        if limit is None:
            return {
                "resource_type": resource_type,
                "allowed": True,
                "used": used,
                "limit": None,
                "remaining": None,
                "message": "Unlimited plan limit.",
            }

        remaining = limit - used
        allowed = used < limit
        label = SubscriptionService.RESOURCE_LABELS[resource_type]
        message = (
            f"Plan limit reached for {label}: {used}/{limit}. Upgrade your subscription to continue."
            if not allowed
            else f"{label.capitalize()} usage: {used}/{limit}."
        )
        return {
            "resource_type": resource_type,
            "allowed": allowed,
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "message": message,
        }

    @staticmethod
    def enforce_limits(pharmacy, resource_type):
        limit_status = SubscriptionService.check_limit(pharmacy, resource_type)
        if not limit_status["allowed"]:
            raise ValidationError({"subscription": limit_status["message"]})
        return limit_status

    @staticmethod
    def apply_plan_defaults(pharmacy, plan_type=None):
        if pharmacy is None:
            raise ValidationError({"pharmacy": "Pharmacy is required."})

        resolved_plan = plan_type or pharmacy.plan_type or "BASIC"
        if resolved_plan not in SubscriptionService.PLAN_LIMITS:
            raise ValidationError({"plan_type": "Invalid plan type."})

        limits = SubscriptionService.PLAN_LIMITS[resolved_plan]
        now = timezone.now()

        pharmacy.plan_type = resolved_plan
        pharmacy.max_users = limits["max_users"]
        pharmacy.max_medicines = limits["max_medicines"]
        pharmacy.max_monthly_sales = limits["max_monthly_sales"]
        pharmacy.is_active = True if pharmacy.is_active is None else pharmacy.is_active
        if pharmacy.subscription_start is None:
            pharmacy.subscription_start = now
        if pharmacy.subscription_end is None:
            pharmacy.subscription_end = pharmacy.subscription_start + timedelta(days=30)
        pharmacy.save(
            update_fields=[
                "plan_type",
                "max_users",
                "max_medicines",
                "max_monthly_sales",
                "is_active",
                "subscription_start",
                "subscription_end",
            ]
        )
        return pharmacy
