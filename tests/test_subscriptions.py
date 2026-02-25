from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.medicines.models import Medicine
from apps.sales.models import Sale
from apps.tenants.models import Pharmacy
from apps.tenants.services import SubscriptionService


class SubscriptionServiceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="sub_owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.pharmacy = Pharmacy.objects.create(
            name="Subscription Pharmacy",
            owner=self.owner,
            plan_type=Pharmacy.PlanType.BASIC,
        )
        self.owner.pharmacy = self.pharmacy
        self.owner.save(update_fields=["pharmacy"])

        self.superuser = User.objects.create_superuser(
            username="super_limit",
            email="super_limit@example.com",
            password="pass12345",
        )

    def test_plan_defaults_applied_for_basic_pro_and_enterprise(self):
        self.assertEqual(self.pharmacy.max_users, 3)
        self.assertEqual(self.pharmacy.max_medicines, 200)
        self.assertEqual(self.pharmacy.max_monthly_sales, 1000)

        pro = Pharmacy.objects.create(name="Pro Pharmacy", owner=self.owner, plan_type=Pharmacy.PlanType.PRO)
        self.assertEqual(pro.max_users, 10)
        self.assertEqual(pro.max_medicines, 2000)
        self.assertEqual(pro.max_monthly_sales, 10000)

        enterprise = Pharmacy.objects.create(
            name="Enterprise Pharmacy",
            owner=self.owner,
            plan_type=Pharmacy.PlanType.ENTERPRISE,
        )
        self.assertIsNone(enterprise.max_users)
        self.assertIsNone(enterprise.max_medicines)
        self.assertIsNone(enterprise.max_monthly_sales)

    def test_days_remaining_returns_integer(self):
        self.pharmacy.subscription_end = timezone.now() + timedelta(days=5, hours=1)
        self.pharmacy.save(update_fields=["subscription_end"])
        remaining = SubscriptionService.days_remaining(self.pharmacy)
        self.assertGreaterEqual(remaining, 4)
        self.assertLessEqual(remaining, 5)

    def test_user_limit_blocks_fourth_user_on_basic(self):
        User.objects.create_user(
            username="sub_user_1",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy,
        )
        User.objects.create_user(
            username="sub_user_2",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy,
        )
        with self.assertRaises(ValidationError):
            SubscriptionService.enforce_limits(self.pharmacy, SubscriptionService.RESOURCE_USERS)

    def test_medicine_limit_blocks_201st_medicine_on_basic(self):
        medicines = []
        for idx in range(200):
            medicines.append(
                Medicine(
                    name=f"Medicine {idx}",
                    sku=f"SUB-MED-{idx}",
                    unit_price=Decimal("1000.00"),
                    pharmacy=self.pharmacy,
                )
            )
        Medicine.objects.bulk_create(medicines, batch_size=100)

        with self.assertRaises(ValidationError):
            SubscriptionService.enforce_limits(self.pharmacy, SubscriptionService.RESOURCE_MEDICINES)

    def test_monthly_sales_limit_blocks_1001st_sale_on_basic(self):
        now = timezone.now()
        sales = []
        for _ in range(1000):
            sales.append(
                Sale(
                    date=now,
                    total_amount=Decimal("1.00"),
                    user=self.owner,
                    pharmacy=self.pharmacy,
                )
            )
        Sale.objects.bulk_create(sales, batch_size=200)

        with self.assertRaises(ValidationError):
            SubscriptionService.enforce_limits(self.pharmacy, SubscriptionService.RESOURCE_MONTHLY_SALES)

    def test_superuser_bypass_for_medicine_limit(self):
        self.pharmacy.max_medicines = 0
        self.pharmacy.save(update_fields=["max_medicines"])

        self.client.force_login(self.superuser)
        response = self.client.post(
            "/api/medicines/medicines/",
            data={
                "name": "Superuser Medicine",
                "sku": "SUPER-MED-1",
                "unit_price": "1000.00",
                "pharmacy": self.pharmacy.id,
            },
        )
        self.assertEqual(response.status_code, 201)
