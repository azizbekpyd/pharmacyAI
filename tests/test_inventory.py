import json
from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.inventory.models import Inventory
from apps.medicines.models import Medicine
from apps.medicines.services import MedicineService
from apps.tenants.models import Pharmacy


class InventoryFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="inventory_owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.pharmacy = Pharmacy.objects.create(name="Inventory Pharmacy", owner=self.owner)
        self.manager = User.objects.create_user(
            username="inventory_manager",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy,
        )

    def test_initial_stock_propagates_when_creating_medicine_from_template_view(self):
        self.client.force_login(self.manager)

        response = self.client.post(
            "/medicines/create/",
            data=json.dumps(
                {
                    "name": "Nurofen",
                    "sku": "NUR-001",
                    "unit_price": "30000.00",
                    "initial_stock": 37,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        medicine = Medicine.objects.get(sku="NUR-001", pharmacy=self.pharmacy)
        inventory = Inventory.objects.get(medicine=medicine)
        self.assertEqual(inventory.current_stock, 37)
        self.assertEqual(inventory.pharmacy_id, medicine.pharmacy_id)

    def test_service_creates_single_inventory_record(self):
        medicine = MedicineService.create_medicine_with_inventory(
            pharmacy=self.pharmacy,
            medicine_data={
                "name": "Validol",
                "sku": "VAL-001",
                "unit_price": Decimal("2500.00"),
            },
            initial_stock=11,
        )

        self.assertEqual(Inventory.objects.filter(medicine=medicine).count(), 1)
        inventory = Inventory.objects.get(medicine=medicine)
        self.assertEqual(inventory.current_stock, 11)
        self.assertEqual(inventory.pharmacy, self.pharmacy)
