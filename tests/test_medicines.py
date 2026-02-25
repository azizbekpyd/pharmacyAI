import json
from decimal import Decimal

from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase

from apps.accounts.models import User
from apps.inventory.models import Inventory
from apps.medicines.models import Medicine
from apps.tenants.models import Pharmacy


class MedicineCRUDTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.pharmacy_a = Pharmacy.objects.create(name="Pharmacy A", owner=self.owner)
        self.pharmacy_b = Pharmacy.objects.create(name="Pharmacy B", owner=self.owner)

        self.admin_a = User.objects.create_user(
            username="admin_a",
            password="pass12345",
            role=User.ROLE_ADMIN,
            pharmacy=self.pharmacy_a,
        )
        self.manager_a = User.objects.create_user(
            username="manager_a",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy_a,
        )

    def test_medicine_create_edit_delete_flow(self):
        self.client.force_login(self.admin_a)

        create_response = self.client.post(
            "/medicines/create/",
            data=json.dumps(
                {
                    "name": "Paracetamol",
                    "sku": "PARA-001",
                    "unit_price": "12000.00",
                    "initial_stock": 15,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)

        medicine = Medicine.objects.get(sku="PARA-001", pharmacy=self.pharmacy_a)
        inventory = Inventory.objects.get(medicine=medicine)
        self.assertEqual(inventory.current_stock, 15)

        update_response = self.client.post(
            f"/medicines/{medicine.id}/edit/",
            data={
                "name": "Paracetamol Forte",
                "category": "",
                "unit_price": "15000.00",
                "stock": "22",
                "expiry_date": "",
                "description": "Updated",
            },
        )
        self.assertEqual(update_response.status_code, 302)

        medicine.refresh_from_db()
        inventory.refresh_from_db()
        self.assertEqual(medicine.name, "Paracetamol Forte")
        self.assertEqual(medicine.unit_price, Decimal("15000.00"))
        self.assertEqual(inventory.current_stock, 22)

        delete_response = self.client.post(f"/medicines/{medicine.id}/delete/")
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(Medicine.objects.filter(id=medicine.id).exists())

    def test_manager_cannot_delete_medicine(self):
        medicine = Medicine.objects.create(
            name="Ibuprofen",
            sku="IBU-001",
            unit_price=Decimal("10000.00"),
            pharmacy=self.pharmacy_a,
        )
        Inventory.objects.create(medicine=medicine, pharmacy=self.pharmacy_a, current_stock=10)

        self.client.force_login(self.manager_a)
        response = self.client.post(f"/medicines/{medicine.id}/delete/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Medicine.objects.filter(id=medicine.id).exists())

    def test_duplicate_sku_allowed_across_pharmacies_but_not_within_same_pharmacy(self):
        Medicine.objects.create(
            name="Amoxicillin A",
            sku="SKU-SHARED",
            unit_price=Decimal("18000.00"),
            pharmacy=self.pharmacy_a,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Medicine.objects.create(
                    name="Amoxicillin Duplicate A",
                    sku="SKU-SHARED",
                    unit_price=Decimal("18000.00"),
                    pharmacy=self.pharmacy_a,
                )

        other = Medicine.objects.create(
            name="Amoxicillin B",
            sku="SKU-SHARED",
            unit_price=Decimal("20000.00"),
            pharmacy=self.pharmacy_b,
        )
        self.assertEqual(other.sku, "SKU-SHARED")
