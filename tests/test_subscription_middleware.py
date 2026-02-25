import json
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import Inventory
from apps.medicines.models import Medicine
from apps.tenants.models import Pharmacy


class SubscriptionMiddlewareTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="mw_owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.pharmacy = Pharmacy.objects.create(
            name="Middleware Pharmacy",
            owner=self.owner,
            plan_type=Pharmacy.PlanType.BASIC,
            subscription_start=timezone.now() - timedelta(days=30),
            subscription_end=timezone.now() + timedelta(days=30),
            is_active=True,
        )
        self.owner.pharmacy = self.pharmacy
        self.owner.save(update_fields=["pharmacy"])

        self.manager = User.objects.create_user(
            username="mw_manager",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy,
        )
        self.medicine = Medicine.objects.create(
            name="Middleware Medicine",
            sku="MW-MED-1",
            unit_price=Decimal("5000.00"),
            pharmacy=self.pharmacy,
        )
        Inventory.objects.create(medicine=self.medicine, pharmacy=self.pharmacy, current_stock=20)

    def test_expired_subscription_allows_read_only(self):
        self.pharmacy.subscription_end = timezone.now() - timedelta(days=1)
        self.pharmacy.save(update_fields=["subscription_end"])

        self.client.force_login(self.manager)

        read_response = self.client.get("/medicines/")
        self.assertEqual(read_response.status_code, 200)

        write_template = self.client.post(
            "/medicines/create/",
            data={
                "name": "Blocked Medicine",
                "sku": "MW-MED-BLOCK",
                "unit_price": "1000.00",
                "initial_stock": 1,
            },
        )
        self.assertEqual(write_template.status_code, 302)

        write_api = self.client.post(
            "/api/sales/sales/",
            data=json.dumps(
                {
                    "notes": "Blocked sale",
                    "items": [
                        {
                            "medicine_id": self.medicine.id,
                            "quantity": 1,
                            "unit_price": "5000.00",
                        }
                    ],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(write_api.status_code, 403)
        self.assertIn("Subscription expired", write_api.json().get("detail", ""))

    def test_demo_mode_blocks_write_then_allows_after_disable(self):
        self.client.force_login(self.manager)

        enable_demo = self.client.get("/dashboard/?demo=true")
        self.assertEqual(enable_demo.status_code, 200)
        self.assertTrue(self.client.session.get("demo_mode"))

        blocked = self.client.post(
            "/api/medicines/medicines/",
            data=json.dumps(
                {
                    "name": "Demo Blocked",
                    "sku": "MW-DEMO-1",
                    "unit_price": "1000.00",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertEqual(blocked.json().get("detail"), "Demo mode is read-only.")

        disable_demo = self.client.get("/dashboard/?demo=false")
        self.assertEqual(disable_demo.status_code, 200)
        self.assertFalse(self.client.session.get("demo_mode"))

        allowed = self.client.post(
            "/api/medicines/medicines/",
            data=json.dumps(
                {
                    "name": "Demo Allowed",
                    "sku": "MW-DEMO-2",
                    "unit_price": "1000.00",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(allowed.status_code, 201)
