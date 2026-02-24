from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import models, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import Inventory, ReorderRecommendation
from apps.medicines.models import Category, Medicine
from apps.sales.models import Sale, SaleItem
from apps.tenants.models import Pharmacy


class Command(BaseCommand):
    help = "Seed demo tenant data for Pharmacy Alpha and Pharmacy Beta."

    DEMO_PHARMACIES = ("Pharmacy Alpha", "Pharmacy Beta")
    DEFAULT_PASSWORD = "DemoPass123!"

    BLUEPRINTS = {
        "Pharmacy Alpha": {
            "label": "ALPHA",
            "categories": [
                ("Pain Relief", "Pain and inflammation medicines."),
                ("Antibiotics", "Bacterial infection treatment medicines."),
                ("Cardio Care", "Heart and blood circulation medicines."),
            ],
            "medicines": [
                {"name": "Paracetamol 500mg", "sku": "A-MED-001", "category": "Pain Relief", "unit_price": Decimal("12000"), "expiry_days": 320},
                {"name": "Diclofenac Gel 1%", "sku": "A-MED-002", "category": "Pain Relief", "unit_price": Decimal("42000"), "expiry_days": 260},
                {"name": "Amoxicillin 500mg", "sku": "A-MED-003", "category": "Antibiotics", "unit_price": Decimal("47000"), "expiry_days": 240},
                {"name": "Cefixime 200mg", "sku": "A-MED-004", "category": "Antibiotics", "unit_price": Decimal("68000"), "expiry_days": 220},
                {"name": "Aspirin Cardio 100mg", "sku": "A-MED-005", "category": "Cardio Care", "unit_price": Decimal("26000"), "expiry_days": 365},
            ],
            "inventory": {
                "A-MED-001": {"current": 140, "min": 35, "max": 220},
                "A-MED-002": {"current": 55, "min": 20, "max": 120},
                "A-MED-003": {"current": 70, "min": 25, "max": 150},
                "A-MED-004": {"current": 30, "min": 15, "max": 90},
                "A-MED-005": {"current": 95, "min": 30, "max": 170},
            },
            "sales": [
                {"note": "ALPHA-DEMO-SALE-1", "days_ago": 3, "items": [("A-MED-001", 3), ("A-MED-005", 1)]},
                {"note": "ALPHA-DEMO-SALE-2", "days_ago": 2, "items": [("A-MED-003", 2), ("A-MED-002", 1)]},
                {"note": "ALPHA-DEMO-SALE-3", "days_ago": 1, "items": [("A-MED-004", 1), ("A-MED-001", 2)]},
            ],
        },
        "Pharmacy Beta": {
            "label": "BETA",
            "categories": [
                ("Cold & Flu", "Respiratory symptom relief medicines."),
                ("Digestive Health", "Stomach and gut treatment medicines."),
                ("Vitamins & Supplements", "Nutritional supplements and immunity support."),
            ],
            "medicines": [
                {"name": "Nasal Spray 15ml", "sku": "B-MED-001", "category": "Cold & Flu", "unit_price": Decimal("36000"), "expiry_days": 300},
                {"name": "Cough Syrup 100ml", "sku": "B-MED-002", "category": "Cold & Flu", "unit_price": Decimal("29500"), "expiry_days": 180},
                {"name": "Omeprazole 20mg", "sku": "B-MED-003", "category": "Digestive Health", "unit_price": Decimal("34000"), "expiry_days": 250},
                {"name": "Probiotic Capsules", "sku": "B-MED-004", "category": "Digestive Health", "unit_price": Decimal("81000"), "expiry_days": 340},
                {"name": "Vitamin D3 2000 IU", "sku": "B-MED-005", "category": "Vitamins & Supplements", "unit_price": Decimal("45000"), "expiry_days": 365},
            ],
            "inventory": {
                "B-MED-001": {"current": 60, "min": 20, "max": 130},
                "B-MED-002": {"current": 120, "min": 40, "max": 210},
                "B-MED-003": {"current": 48, "min": 18, "max": 110},
                "B-MED-004": {"current": 26, "min": 12, "max": 80},
                "B-MED-005": {"current": 150, "min": 45, "max": 260},
            },
            "sales": [
                {"note": "BETA-DEMO-SALE-1", "days_ago": 3, "items": [("B-MED-002", 2), ("B-MED-005", 2)]},
                {"note": "BETA-DEMO-SALE-2", "days_ago": 2, "items": [("B-MED-003", 1), ("B-MED-001", 1)]},
                {"note": "BETA-DEMO-SALE-3", "days_ago": 1, "items": [("B-MED-004", 1), ("B-MED-002", 1), ("B-MED-005", 1)]},
            ],
        },
    }

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding demo tenants..."))

        self._clear_previous_demo_pharmacies()
        _, alpha_admin, beta_admin = self._ensure_users()
        alpha_pharmacy, beta_pharmacy = self._ensure_demo_pharmacies(alpha_admin, beta_admin)

        self._seed_pharmacy_data(alpha_pharmacy, alpha_admin)
        self._seed_pharmacy_data(beta_pharmacy, beta_admin)

        self._run_consistency_checks(alpha_pharmacy, beta_pharmacy)
        self.stdout.write(self.style.SUCCESS("Demo tenant seed completed successfully."))
        self._print_credentials()

    def _clear_previous_demo_pharmacies(self):
        qs = Pharmacy.objects.filter(name__in=self.DEMO_PHARMACIES)
        count = qs.count()
        if count:
            demo_ids = list(qs.values_list("id", flat=True))
            SaleItem.objects.filter(pharmacy_id__in=demo_ids).delete()
            Sale.objects.filter(pharmacy_id__in=demo_ids).delete()
            ReorderRecommendation.objects.filter(pharmacy_id__in=demo_ids).delete()
            Inventory.objects.filter(pharmacy_id__in=demo_ids).delete()
            Medicine.objects.filter(pharmacy_id__in=demo_ids).delete()
            Category.objects.filter(pharmacy_id__in=demo_ids).delete()
            Pharmacy.objects.filter(id__in=demo_ids).delete()
            self.stdout.write(self.style.WARNING(f"Removed {count} previous demo pharmacy records (and related tenant data)."))
        else:
            self.stdout.write("No previous demo pharmacies found.")

    def _ensure_users(self):
        superadmin, _ = User.objects.get_or_create(
            username="superadmin",
            defaults={
                "email": "superadmin@example.com",
                "first_name": "Super",
                "last_name": "Admin",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        superadmin.email = "superadmin@example.com"
        superadmin.first_name = "Super"
        superadmin.last_name = "Admin"
        superadmin.role = "ADMIN"
        superadmin.is_staff = True
        superadmin.is_superuser = True
        superadmin.pharmacy = None
        superadmin.set_password(self.DEFAULT_PASSWORD)
        superadmin.save()

        alpha_admin, _ = User.objects.get_or_create(
            username="alpha_admin",
            defaults={
                "email": "alpha_admin@example.com",
                "first_name": "Alpha",
                "last_name": "Admin",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": False,
            },
        )
        alpha_admin.email = "alpha_admin@example.com"
        alpha_admin.first_name = "Alpha"
        alpha_admin.last_name = "Admin"
        alpha_admin.role = "ADMIN"
        alpha_admin.is_staff = True
        alpha_admin.is_superuser = False
        alpha_admin.set_password(self.DEFAULT_PASSWORD)
        alpha_admin.save()

        beta_admin, _ = User.objects.get_or_create(
            username="beta_admin",
            defaults={
                "email": "beta_admin@example.com",
                "first_name": "Beta",
                "last_name": "Admin",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": False,
            },
        )
        beta_admin.email = "beta_admin@example.com"
        beta_admin.first_name = "Beta"
        beta_admin.last_name = "Admin"
        beta_admin.role = "ADMIN"
        beta_admin.is_staff = True
        beta_admin.is_superuser = False
        beta_admin.set_password(self.DEFAULT_PASSWORD)
        beta_admin.save()

        self.stdout.write("Users created/updated: superadmin, alpha_admin, beta_admin")
        return superadmin, alpha_admin, beta_admin

    def _ensure_demo_pharmacies(self, alpha_admin, beta_admin):
        alpha_pharmacy, _ = Pharmacy.objects.get_or_create(
            name="Pharmacy Alpha",
            defaults={"owner": alpha_admin, "plan_type": Pharmacy.PlanType.PRO},
        )
        alpha_pharmacy.owner = alpha_admin
        alpha_pharmacy.plan_type = Pharmacy.PlanType.PRO
        alpha_pharmacy.save(update_fields=["owner", "plan_type"])

        beta_pharmacy, _ = Pharmacy.objects.get_or_create(
            name="Pharmacy Beta",
            defaults={"owner": beta_admin, "plan_type": Pharmacy.PlanType.BASIC},
        )
        beta_pharmacy.owner = beta_admin
        beta_pharmacy.plan_type = Pharmacy.PlanType.BASIC
        beta_pharmacy.save(update_fields=["owner", "plan_type"])

        alpha_admin.pharmacy = alpha_pharmacy
        alpha_admin.save(update_fields=["pharmacy"])
        beta_admin.pharmacy = beta_pharmacy
        beta_admin.save(update_fields=["pharmacy"])

        self.stdout.write("Pharmacies created/updated: Pharmacy Alpha, Pharmacy Beta")
        return alpha_pharmacy, beta_pharmacy

    def _seed_pharmacy_data(self, pharmacy, admin_user):
        blueprint = self.BLUEPRINTS[pharmacy.name]
        categories = self._create_categories(pharmacy, blueprint["categories"])
        medicines = self._create_medicines(pharmacy, categories, blueprint["medicines"], blueprint["label"])
        self._create_inventory(pharmacy, medicines, blueprint["inventory"])
        self._create_sales(pharmacy, admin_user, medicines, blueprint["sales"])
        self.stdout.write(self.style.SUCCESS(f"Seeded data for {pharmacy.name}"))

    def _create_categories(self, pharmacy, category_data):
        categories = {}
        for name, description in category_data:
            category, _ = Category.objects.get_or_create(
                pharmacy=pharmacy,
                name=name,
                defaults={"description": description},
            )
            if category.description != description:
                category.description = description
                category.save(update_fields=["description"])
            categories[name] = category
        return categories

    def _create_medicines(self, pharmacy, categories, medicine_data, label):
        medicines = {}
        for item in medicine_data:
            category = categories[item["category"]]
            medicine, _ = Medicine.objects.get_or_create(
                pharmacy=pharmacy,
                sku=item["sku"],
                defaults={
                    "name": item["name"],
                    "category": category,
                    "description": f"{label} demo medicine: {item['name']}",
                    "unit_price": item["unit_price"],
                    "expiry_date": timezone.localdate() + timedelta(days=item["expiry_days"]),
                },
            )
            medicine.name = item["name"]
            medicine.category = category
            medicine.description = f"{label} demo medicine: {item['name']}"
            medicine.unit_price = item["unit_price"]
            medicine.expiry_date = timezone.localdate() + timedelta(days=item["expiry_days"])
            medicine.save()
            medicines[item["sku"]] = medicine
        return medicines

    def _create_inventory(self, pharmacy, medicines, stock_map):
        for sku, medicine in medicines.items():
            cfg = stock_map[sku]
            inventory, _ = Inventory.objects.get_or_create(
                medicine=medicine,
                pharmacy=pharmacy,
                defaults={
                    "current_stock": cfg["current"],
                    "min_stock_level": cfg["min"],
                    "max_stock_level": cfg["max"],
                    "last_restocked_date": timezone.now() - timedelta(days=3),
                },
            )
            inventory.pharmacy = pharmacy
            inventory.current_stock = cfg["current"]
            inventory.min_stock_level = cfg["min"]
            inventory.max_stock_level = cfg["max"]
            inventory.last_restocked_date = timezone.now() - timedelta(days=3)
            inventory.save()

    def _create_sales(self, pharmacy, admin_user, medicines, sales_blueprint):
        for idx, sale_cfg in enumerate(sales_blueprint, start=1):
            sale, _ = Sale.objects.get_or_create(
                pharmacy=pharmacy,
                notes=sale_cfg["note"],
                defaults={
                    "user": admin_user,
                    "total_amount": Decimal("0.01"),
                },
            )
            sale.user = admin_user
            sale.pharmacy = pharmacy
            sale.total_amount = Decimal("0.01")
            sale.save()

            sale_date = timezone.make_aware(
                datetime.combine(timezone.localdate() - timedelta(days=sale_cfg["days_ago"]), time(hour=10 + idx, minute=15)),
                timezone.get_current_timezone(),
            )
            Sale.objects.filter(pk=sale.pk).update(date=sale_date)

            sale.items.all().delete()
            total_amount = Decimal("0.00")
            for sku, qty in sale_cfg["items"]:
                medicine = medicines[sku]
                if medicine.pharmacy_id != pharmacy.id:
                    raise ValueError("Cross-tenant medicine assignment detected during demo seed.")

                item = SaleItem.objects.create(
                    sale=sale,
                    pharmacy=pharmacy,
                    medicine=medicine,
                    quantity=qty,
                    unit_price=medicine.unit_price,
                )
                total_amount += item.subtotal

            if total_amount <= 0:
                total_amount = Decimal("0.01")
            sale.total_amount = total_amount
            sale.save(update_fields=["total_amount", "updated_at"])

    def _run_consistency_checks(self, alpha_pharmacy, beta_pharmacy):
        demo_ids = [alpha_pharmacy.id, beta_pharmacy.id]

        mismatch_saleitems = SaleItem.objects.filter(pharmacy__id__in=demo_ids).exclude(pharmacy_id=models.F("sale__pharmacy_id")).count()
        if mismatch_saleitems:
            raise ValueError("Found SaleItem rows where SaleItem.pharmacy != Sale.pharmacy")

        mismatch_inventory = Inventory.objects.filter(pharmacy__id__in=demo_ids).exclude(pharmacy_id=models.F("medicine__pharmacy_id")).count()
        if mismatch_inventory:
            raise ValueError("Found Inventory rows where Inventory.pharmacy != Inventory.medicine.pharmacy")

    def _print_credentials(self):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo login credentials:"))
        self.stdout.write("  superadmin / DemoPass123!  (superuser, all tenants)")
        self.stdout.write("  alpha_admin / DemoPass123! (Pharmacy Alpha)")
        self.stdout.write("  beta_admin  / DemoPass123! (Pharmacy Beta)")

