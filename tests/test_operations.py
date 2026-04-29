from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import User
from apps.inventory.models import ActivityLog, Inventory, PurchaseOrder, StockMovement, Supplier
from apps.medicines.models import Medicine
from apps.tenants.models import Pharmacy


class OperationsWorkflowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner",
            password="pass12345",
            role=User.ROLE_OWNER,
        )
        self.pharmacy = Pharmacy.objects.create(name="Operations Pharmacy", owner=self.owner)
        self.owner.pharmacy = self.pharmacy
        self.owner.save(update_fields=["pharmacy"])

        self.cashier = User.objects.create_user(
            username="cashier",
            password="pass12345",
            role=User.ROLE_CASHIER,
            pharmacy=self.pharmacy,
        )
        self.medicine = Medicine.objects.create(
            pharmacy=self.pharmacy,
            name="Barcode Paracetamol",
            sku="BAR-001",
            barcode="860000000001",
            unit_price=Decimal("12000.00"),
            cost_price=Decimal("7000.00"),
        )
        self.inventory = Inventory.objects.create(
            pharmacy=self.pharmacy,
            medicine=self.medicine,
            current_stock=20,
            min_stock_level=5,
            max_stock_level=50,
        )

    def test_barcode_lookup_and_csv_export(self):
        self.client.force_login(self.owner)
        response = self.client.get("/api/medicines/medicines/?barcode=860000000001")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["sku"], "BAR-001")

        export_response = self.client.get("/api/medicines/medicines/export_csv/")
        self.assertEqual(export_response.status_code, 200)
        self.assertIn("text/csv", export_response["Content-Type"])
        self.assertIn("860000000001", export_response.content.decode())

    def test_cashier_sale_creates_stock_movement_and_activity_log(self):
        self.client.force_login(self.cashier)
        response = self.client.post(
            "/api/sales/sales/",
            data={
                "notes": "Cashier checkout",
                "items": [
                    {
                        "medicine_id": self.medicine.id,
                        "quantity": 2,
                        "unit_price": "12000.00",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.current_stock, 18)

        movement = StockMovement.objects.get(medicine=self.medicine)
        self.assertEqual(movement.movement_type, StockMovement.TYPE_SALE)
        self.assertEqual(movement.quantity_change, -2)
        self.assertEqual(movement.stock_after, 18)

        self.assertTrue(ActivityLog.objects.filter(action=ActivityLog.ACTION_SALE).exists())

    def test_purchase_order_receive_adds_stock_and_updates_cost(self):
        self.client.force_login(self.owner)
        supplier = Supplier.objects.create(pharmacy=self.pharmacy, name="Main Supplier")
        create_response = self.client.post(
            "/api/inventory/purchase-orders/",
            data={
                "supplier": supplier.id,
                "reference_number": "PO-001",
                "items": [
                    {
                        "medicine_id": self.medicine.id,
                        "quantity": 5,
                        "unit_cost": "8000.00",
                    }
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 201)
        purchase_order_id = create_response.json()["id"]

        receive_response = self.client.post(f"/api/inventory/purchase-orders/{purchase_order_id}/receive/")
        self.assertEqual(receive_response.status_code, 200)

        self.inventory.refresh_from_db()
        self.medicine.refresh_from_db()
        purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
        self.assertEqual(purchase_order.status, PurchaseOrder.STATUS_RECEIVED)
        self.assertEqual(self.inventory.current_stock, 25)
        self.assertEqual(self.medicine.cost_price, Decimal("8000.00"))
        self.assertTrue(
            StockMovement.objects.filter(
                medicine=self.medicine,
                movement_type=StockMovement.TYPE_PURCHASE,
                quantity_change=5,
            ).exists()
        )
