from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.inventory.models import Inventory
from apps.medicines.models import Medicine
from apps.sales.models import Sale
from apps.tenants.models import Pharmacy


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="tenant_owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.pharmacy_a = Pharmacy.objects.create(name="Tenant A", owner=self.owner)
        self.pharmacy_b = Pharmacy.objects.create(name="Tenant B", owner=self.owner)

        self.manager_a = User.objects.create_user(
            username="manager_tenant_a",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy_a,
        )
        self.admin_a = User.objects.create_user(
            username="admin_tenant_a",
            password="pass12345",
            role=User.ROLE_ADMIN,
            pharmacy=self.pharmacy_a,
        )
        self.manager_b = User.objects.create_user(
            username="manager_tenant_b",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy_b,
        )

        self.medicine_a = Medicine.objects.create(
            name="Aspirin A",
            sku="ASP-A",
            unit_price=Decimal("12000.00"),
            pharmacy=self.pharmacy_a,
        )
        self.medicine_b = Medicine.objects.create(
            name="Aspirin B",
            sku="ASP-B",
            unit_price=Decimal("13000.00"),
            pharmacy=self.pharmacy_b,
        )

        Inventory.objects.create(medicine=self.medicine_a, pharmacy=self.pharmacy_a, current_stock=5)
        Inventory.objects.create(medicine=self.medicine_b, pharmacy=self.pharmacy_b, current_stock=9)

    def test_non_superuser_cannot_see_other_pharmacy_data(self):
        self.client.force_login(self.manager_a)

        medicines_response = self.client.get("/api/medicines/medicines/")
        self.assertEqual(medicines_response.status_code, 200)
        medicines = medicines_response.json()["results"]
        medicine_ids = {row["id"] for row in medicines}
        self.assertIn(self.medicine_a.id, medicine_ids)
        self.assertNotIn(self.medicine_b.id, medicine_ids)

        sales_response = self.client.get("/api/sales/sales/")
        self.assertEqual(sales_response.status_code, 200)
        self.assertEqual(sales_response.json()["count"], Sale.objects.filter(pharmacy=self.pharmacy_a).count())

    def test_cross_tenant_read_access_returns_404(self):
        self.client.force_login(self.manager_a)

        api_response = self.client.get(f"/api/medicines/medicines/{self.medicine_b.id}/")
        self.assertEqual(api_response.status_code, 404)

        template_response = self.client.get(f"/medicines/{self.medicine_b.id}/")
        self.assertEqual(template_response.status_code, 404)

    def test_cross_tenant_delete_returns_404_for_non_superuser(self):
        self.client.force_login(self.admin_a)

        response = self.client.post(f"/medicines/{self.medicine_b.id}/delete/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Medicine.objects.filter(id=self.medicine_b.id).exists())
