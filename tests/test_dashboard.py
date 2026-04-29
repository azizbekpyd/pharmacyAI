import json
import re
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import Inventory
from apps.medicines.models import Category, Medicine
from apps.sales.models import Sale, SaleItem
from apps.tenants.models import Pharmacy


class DashboardRenderingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="dashboard_owner",
            password="pass12345",
            role=User.ROLE_ADMIN,
        )
        self.pharmacy = Pharmacy.objects.create(name="Dashboard Pharmacy", owner=self.owner)
        self.user = User.objects.create_user(
            username="dashboard_manager",
            password="pass12345",
            role=User.ROLE_MANAGER,
            pharmacy=self.pharmacy,
        )
        self.category = Category.objects.create(name="Pain Relief", pharmacy=self.pharmacy)
        self.medicine = Medicine.objects.create(
            name="Aspirin",
            sku="ASP-001",
            unit_price=Decimal("12000.00"),
            category=self.category,
            pharmacy=self.pharmacy,
        )
        Inventory.objects.create(
            medicine=self.medicine,
            pharmacy=self.pharmacy,
            current_stock=3,
            min_stock_level=5,
            max_stock_level=20,
        )

        current_sale = Sale.objects.create(
            total_amount=Decimal("24000.00"),
            user=self.user,
            pharmacy=self.pharmacy,
        )
        SaleItem.objects.create(
            sale=current_sale,
            pharmacy=self.pharmacy,
            medicine=self.medicine,
            quantity=2,
            unit_price=Decimal("12000.00"),
            subtotal=Decimal("24000.00"),
        )

        previous_sale_1 = Sale.objects.create(
            total_amount=Decimal("12000.00"),
            user=self.user,
            pharmacy=self.pharmacy,
        )
        previous_sale_2 = Sale.objects.create(
            total_amount=Decimal("12000.00"),
            user=self.user,
            pharmacy=self.pharmacy,
        )

        now = timezone.now()
        Sale.objects.filter(id=current_sale.id).update(date=now - timedelta(days=2))
        Sale.objects.filter(id=previous_sale_1.id).update(date=now - timedelta(days=35))
        Sale.objects.filter(id=previous_sale_2.id).update(date=now - timedelta(days=40))

    @override_settings(ALLOWED_HOSTS=["testserver", "127.0.0.1", "localhost"])
    def test_dashboard_embeds_valid_json_payload_in_uzbek_locale(self):
        self.client.force_login(self.user)

        response = self.client.get("/dashboard/", HTTP_ACCEPT_LANGUAGE="uz")

        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        match = re.search(r"const DASHBOARD = (\{.*?\});", html, re.S)
        self.assertIsNotNone(match)

        payload = json.loads(match.group(1))

        self.assertEqual(payload["totalSales"], 1)
        self.assertEqual(payload["medicinesCount"], 1)
        self.assertEqual(payload["lowStockCount"], 1)
        self.assertAlmostEqual(payload["salesGrowthPct"], -50.0)
        self.assertEqual(payload["categoryLabels"], ["Pain Relief"])
        self.assertEqual(payload["categoryRevenue"], [24000.0])
        self.assertEqual(payload["trendSales"], [1])
