import json
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.inventory.models import Inventory
from apps.medicines.models import Medicine
from apps.sales.models import Sale, SaleItem
from apps.tenants.models import Pharmacy


class SalesFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="sales_owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.pharmacy = Pharmacy.objects.create(name="Sales Pharmacy", owner=self.owner)
        self.pharmacist = User.objects.create_user(
            username="sales_pharmacist",
            password="pass12345",
            role=User.ROLE_PHARMACIST,
            pharmacy=self.pharmacy,
        )
        self.medicine = Medicine.objects.create(
            name="Citramon",
            sku="CIT-001",
            unit_price=Decimal("9000.00"),
            pharmacy=self.pharmacy,
        )
        self.inventory = Inventory.objects.create(
            medicine=self.medicine,
            pharmacy=self.pharmacy,
            current_stock=25,
            min_stock_level=2,
            max_stock_level=200,
        )

    def test_pharmacist_can_create_sale_and_total_is_calculated(self):
        self.client.force_login(self.pharmacist)

        response = self.client.post(
            "/api/sales/sales/",
            data=json.dumps(
                {
                    "notes": "Counter sale",
                    "items": [
                        {
                            "medicine_id": self.medicine.id,
                            "quantity": 3,
                            "unit_price": "9500.00",
                        }
                    ],
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json().get("message"), "Sale created successfully")

        sale = Sale.objects.get()
        item = SaleItem.objects.get(sale=sale)
        self.assertEqual(item.subtotal, Decimal("28500.00"))
        self.assertEqual(sale.total_amount, Decimal("28500.00"))

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.current_stock, 22)

    def test_pharmacist_cannot_modify_medicines(self):
        self.client.force_login(self.pharmacist)
        response = self.client.patch(
            f"/api/medicines/medicines/{self.medicine.id}/",
            data=json.dumps({"name": "Blocked"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
