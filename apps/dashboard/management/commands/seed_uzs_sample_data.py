"""
Management command to reset and seed realistic UZS sample data.

This command:
- Removes existing sample data for SaleItem, Sale, Medicine (and dependent inventory/reorder data)
- Creates medicines with realistic Uzbekistan pharmacy prices in UZS
- Creates sales and sale items using those UZS prices
- Recalculates Sale.total_amount from SaleItem subtotals

Usage:
    python manage.py seed_uzs_sample_data
"""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
import random

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import Inventory, ReorderRecommendation
from apps.medicines.models import Category, Medicine
from apps.sales.models import Sale, SaleItem
from apps.tenants.models import Pharmacy


class Command(BaseCommand):
    help = "Reset and seed realistic UZS sample data for diploma demo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of past days to generate sales for (default: 30)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        days = max(7, int(options["days"]))
        random.seed(42)

        self.stdout.write(self.style.WARNING("Resetting sample data..."))
        self._reset_data()
        self.stdout.write(self.style.SUCCESS("Old sample data removed."))

        users = self._ensure_users()
        pharmacy = self._ensure_pharmacy(users[0], users)
        categories = self._create_categories(pharmacy)
        medicines = self._create_medicines(categories, pharmacy)
        self._create_inventory(medicines, pharmacy)
        self._ensure_inventory_records(medicines, pharmacy)
        sales_count, total_revenue = self._create_sales(medicines, users, days, pharmacy)
        self._normalize_inventory_levels(pharmacy)

        self.stdout.write(self.style.SUCCESS("UZS sample data seeded successfully."))
        self.stdout.write(f"Medicines: {len(medicines)}")
        self.stdout.write(f"Sales: {sales_count}")
        self.stdout.write(f"Total Revenue: {total_revenue:,.2f} UZS")

    def _reset_data(self):
        # Order matters because SaleItem has FK to Sale and Medicine(PROTECT).
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        ReorderRecommendation.objects.all().delete()
        Inventory.objects.all().delete()
        Medicine.objects.all().delete()
        Category.objects.all().delete()

    def _ensure_users(self):
        admin, _ = User.objects.get_or_create(
            email="admin@gmail.com",
            defaults={
                "username": "admin",
                "first_name": "Admin",
                "last_name": "User",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password("12345")
        admin.save(update_fields=["password"])

        manager, _ = User.objects.get_or_create(
            email="manager@gmail.com",
            defaults={
                "username": "manager",
                "first_name": "Pharmacy",
                "last_name": "Manager",
                "role": "PHARMACY_MANAGER",
            },
        )
        manager.set_password("12345")
        manager.save(update_fields=["password"])

        return [admin, manager]

    def _ensure_pharmacy(self, owner, users):
        pharmacy, _ = Pharmacy.objects.get_or_create(
            name="Default Pharmacy",
            defaults={
                "owner": owner,
                "plan_type": Pharmacy.PlanType.BASIC,
            },
        )
        if pharmacy.owner_id != owner.id:
            pharmacy.owner = owner
            pharmacy.save(update_fields=["owner"])

        for user in users:
            if user.pharmacy_id != pharmacy.id:
                user.pharmacy = pharmacy
                user.save(update_fields=["pharmacy"])

        return pharmacy

    def _create_categories(self, pharmacy):
        category_names = [
            "Antibiotics",
            "Pain Relief",
            "Vitamins & Supplements",
            "Cold & Flu",
            "Digestive Health",
            "Skin Care",
        ]
        categories = {}
        for name in category_names:
            categories[name] = Category.objects.create(name=name, pharmacy=pharmacy)
        return categories

    def _create_medicines(self, categories, pharmacy):
        # Prices are native UZS values (realistic pharmacy range: 6,000-150,000).
        medicines_data = [
            ("Paracetamol 500mg", "MED001", "Pain Relief", Decimal("12000"), 180),
            ("Amoxicillin 250mg", "MED002", "Antibiotics", Decimal("38000"), 90),
            ("Vitamin C 1000mg", "MED003", "Vitamins & Supplements", Decimal("22000"), 25),
            ("Ibuprofen 400mg", "MED004", "Pain Relief", Decimal("18000"), 200),
            ("Cough Syrup 100ml", "MED005", "Cold & Flu", Decimal("26000"), 15),
            ("Antacid Tablets", "MED006", "Digestive Health", Decimal("9500"), 300),
            ("Multivitamin Complex", "MED007", "Vitamins & Supplements", Decimal("64000"), 120),
            ("Antibacterial Cream", "MED008", "Skin Care", Decimal("28500"), 10),
            ("Aspirin 100mg", "MED009", "Pain Relief", Decimal("8000"), 250),
            ("Probiotics Capsules", "MED010", "Digestive Health", Decimal("78000"), 60),
            ("Nasal Spray", "MED011", "Cold & Flu", Decimal("34000"), 150),
            ("Omega-3 Capsules", "MED012", "Vitamins & Supplements", Decimal("92000"), 210),
        ]

        medicines = []
        for name, sku, category_name, unit_price, expiry_days in medicines_data:
            medicines.append(
                Medicine.objects.create(
                    name=name,
                    sku=sku,
                    category=categories[category_name],
                    pharmacy=pharmacy,
                    unit_price=unit_price,
                    expiry_date=date.today() + timedelta(days=expiry_days),
                    description=f"Sample medicine: {name}",
                )
            )
        return medicines

    def _create_inventory(self, medicines, pharmacy):
        for medicine in medicines:
            current_stock = random.randint(30, 150)
            min_stock = random.randint(15, 40)
            min_stock = min(min_stock, max(10, current_stock - 10))
            max_stock = random.randint(max(current_stock + 40, 120), max(current_stock + 160, 220))

            Inventory.objects.create(
                medicine=medicine,
                pharmacy=pharmacy,
                current_stock=current_stock,
                min_stock_level=min_stock,
                max_stock_level=max_stock,
                last_restocked_date=timezone.now() - timedelta(days=random.randint(1, 30)),
            )

    def _ensure_inventory_records(self, medicines, pharmacy):
        """
        Ensure every medicine has exactly one related inventory record.
        """
        for medicine in medicines:
            Inventory.objects.get_or_create(
                medicine=medicine,
                pharmacy=pharmacy,
                defaults={
                    "pharmacy": pharmacy,
                    "current_stock": random.randint(30, 150),
                    "min_stock_level": random.randint(15, 40),
                    "max_stock_level": random.randint(120, 300),
                    "last_restocked_date": timezone.now() - timedelta(days=random.randint(1, 30)),
                },
            )

    def _normalize_inventory_levels(self, pharmacy):
        """
        Keep seeded inventory practical for demo usage.
        If stock was depleted by generated historical sales, top it up to 30-150 units.
        """
        for inventory in Inventory.objects.select_related("medicine").filter(pharmacy=pharmacy):
            if inventory.current_stock < 30:
                target_stock = random.randint(30, 150)
                inventory.current_stock = target_stock
                inventory.min_stock_level = min(inventory.min_stock_level, max(15, target_stock // 3))
                inventory.max_stock_level = max(inventory.max_stock_level, target_stock + 80)
                inventory.last_restocked_date = timezone.now() - timedelta(days=random.randint(0, 5))
                inventory.save(
                    update_fields=[
                        "current_stock",
                        "min_stock_level",
                        "max_stock_level",
                        "last_restocked_date",
                        "updated_at",
                    ]
                )

    def _create_sales(self, medicines, users, days, pharmacy):
        fast_moving_skus = {"MED001", "MED004", "MED006", "MED009"}
        slow_moving_skus = {"MED008", "MED010"}

        by_sku = {m.sku: m for m in medicines}
        fast_pool = [by_sku[sku] for sku in fast_moving_skus if sku in by_sku]
        slow_pool = [by_sku[sku] for sku in slow_moving_skus if sku in by_sku]
        regular_pool = [m for m in medicines if m.sku not in fast_moving_skus and m.sku not in slow_moving_skus]

        end_day = timezone.localdate()
        start_day = end_day - timedelta(days=days - 1)

        sales_created = 0
        grand_total = Decimal("0.00")

        day = start_day
        while day <= end_day:
            daily_sales_count = random.randint(1, 4)
            for _ in range(daily_sales_count):
                sale = Sale.objects.create(
                    user=random.choice(users),
                    pharmacy=pharmacy,
                    total_amount=Decimal("0.01"),
                    notes=f"Sample UZS sale on {day.isoformat()}",
                )

                sale_dt = timezone.make_aware(
                    datetime.combine(
                        day,
                        time(hour=random.randint(9, 20), minute=random.randint(0, 59)),
                    ),
                    timezone.get_current_timezone(),
                )
                Sale.objects.filter(pk=sale.pk).update(date=sale_dt)

                item_count = random.randint(1, 4)
                sale_total = Decimal("0.00")

                for _ in range(item_count):
                    available_fast = [m for m in fast_pool if m.inventory.current_stock > 0]
                    available_slow = [m for m in slow_pool if m.inventory.current_stock > 0]
                    available_regular = [m for m in regular_pool if m.inventory.current_stock > 0]
                    available_all = [m for m in medicines if m.inventory.current_stock > 0]

                    if not available_all:
                        break

                    roll = random.random()
                    if roll < 0.6 and available_fast:
                        medicine = random.choice(available_fast)
                    elif roll < 0.8 and available_slow:
                        medicine = random.choice(available_slow)
                    else:
                        medicine = random.choice(available_regular or available_all)

                    available_qty = medicine.inventory.current_stock
                    if medicine.sku in fast_moving_skus:
                        min_q = 1
                        max_q = min(4, available_qty)
                    elif medicine.sku in slow_moving_skus:
                        min_q = 1
                        max_q = min(2, available_qty)
                    else:
                        min_q = 1
                        max_q = min(3, available_qty)

                    if max_q < 1:
                        continue
                    quantity = random.randint(min_q, max_q)

                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        pharmacy=pharmacy,
                        medicine=medicine,
                        quantity=quantity,
                        unit_price=medicine.unit_price,
                    )
                    sale_total += sale_item.subtotal

                    inventory = medicine.inventory
                    inventory.current_stock = max(0, inventory.current_stock - quantity)
                    inventory.save(update_fields=["current_stock", "updated_at"])

                Sale.objects.filter(pk=sale.pk).update(total_amount=sale_total)
                sales_created += 1
                grand_total += sale_total

            day += timedelta(days=1)

        return sales_created, grand_total
