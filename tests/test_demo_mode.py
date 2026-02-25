from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.inventory.models import Inventory
from apps.medicines.models import Medicine
from apps.tenants.models import Pharmacy


class DemoModeTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="demo_owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.alpha = Pharmacy.objects.create(name="Pharmacy Alpha", owner=self.owner, plan_type=Pharmacy.PlanType.PRO)
        self.beta = Pharmacy.objects.create(name="Pharmacy Beta", owner=self.owner, plan_type=Pharmacy.PlanType.BASIC)

        self.manager_beta = User.objects.create_user(
            username="demo_manager_beta",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.beta,
        )
        self.admin_beta = User.objects.create_user(
            username="demo_admin_beta",
            password="pass12345",
            role=User.ROLE_ADMIN,
            pharmacy=self.beta,
        )

        self.alpha_medicine = Medicine.objects.create(
            name="Alpha Medicine",
            sku="ALPHA-1",
            unit_price=Decimal("7000.00"),
            pharmacy=self.alpha,
        )
        self.beta_medicine = Medicine.objects.create(
            name="Beta Medicine",
            sku="BETA-1",
            unit_price=Decimal("8000.00"),
            pharmacy=self.beta,
        )
        Inventory.objects.create(medicine=self.alpha_medicine, pharmacy=self.alpha, current_stock=20)
        Inventory.objects.create(medicine=self.beta_medicine, pharmacy=self.beta, current_stock=20)

    def test_demo_mode_switches_read_scope_to_demo_pharmacy(self):
        self.client.force_login(self.manager_beta)

        normal_response = self.client.get("/api/medicines/medicines/")
        normal_ids = {row["id"] for row in normal_response.json()["results"]}
        self.assertIn(self.beta_medicine.id, normal_ids)
        self.assertNotIn(self.alpha_medicine.id, normal_ids)

        demo_response = self.client.get("/api/medicines/medicines/?demo=true")
        demo_ids = {row["id"] for row in demo_response.json()["results"]}
        self.assertIn(self.alpha_medicine.id, demo_ids)
        self.assertNotIn(self.beta_medicine.id, demo_ids)

        persisted_demo_response = self.client.get("/api/medicines/medicines/")
        persisted_ids = {row["id"] for row in persisted_demo_response.json()["results"]}
        self.assertIn(self.alpha_medicine.id, persisted_ids)
        self.assertNotIn(self.beta_medicine.id, persisted_ids)

        self.client.get("/api/medicines/medicines/?demo=false")
        reverted_response = self.client.get("/api/medicines/medicines/")
        reverted_ids = {row["id"] for row in reverted_response.json()["results"]}
        self.assertIn(self.beta_medicine.id, reverted_ids)
        self.assertNotIn(self.alpha_medicine.id, reverted_ids)

    def test_demo_mode_blocks_delete_until_disabled(self):
        self.client.force_login(self.admin_beta)

        self.client.get("/dashboard/?demo=true")
        blocked_delete = self.client.post(f"/medicines/{self.beta_medicine.id}/delete/")
        self.assertEqual(blocked_delete.status_code, 302)
        self.assertTrue(Medicine.objects.filter(id=self.beta_medicine.id).exists())

        self.client.get("/dashboard/?demo=false")
        allowed_delete = self.client.post(f"/medicines/{self.beta_medicine.id}/delete/")
        self.assertEqual(allowed_delete.status_code, 302)
        self.assertFalse(Medicine.objects.filter(id=self.beta_medicine.id).exists())
