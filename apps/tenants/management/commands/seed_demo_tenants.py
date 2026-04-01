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
    help = "Reset demo data to only Pharmacy Alpha, Pharmacy Beta, and superadmin."

    DEMO_PHARMACIES = ("Pharmacy Alpha", "Pharmacy Beta")
    DEMO_USERNAMES = ("superadmin", "alpha", "beta")
    DEFAULT_PASSWORD = "DemoPass123!"

    BLUEPRINTS = {
        "Pharmacy Alpha": {
            "label": "ALPHA",
            "plan_type": Pharmacy.PlanType.PRO,
            "admin": {
                "username": "alpha",
                "email": "alpha@pharmacyai.demo",
                "first_name": "Aziza",
                "last_name": "Karimova",
                "phone_number": "+998901110101",
            },
            "categories": [
                ("Pain Relief", "Fast-moving OTC pain and inflammation medicines."),
                ("Antibiotics", "Prescription antibiotics for common bacterial infections."),
                ("Cardio & BP", "Daily-use therapy for blood pressure and cardiovascular support."),
                ("Diabetes Care", "Core diabetes maintenance medicines."),
            ],
            "medicines": [
                {"name": "Paracetamol 500mg", "sku": "A-PH-001", "category": "Pain Relief", "unit_price": Decimal("12000"), "expiry_days": 320, "description": "High-turnover analgesic for fever and mild pain."},
                {"name": "Ibuprofen 400mg", "sku": "A-PH-002", "category": "Pain Relief", "unit_price": Decimal("18500"), "expiry_days": 280, "description": "Anti-inflammatory tablets for pain, fever, and muscle strain."},
                {"name": "Amoxicillin 500mg", "sku": "A-PH-003", "category": "Antibiotics", "unit_price": Decimal("39000"), "expiry_days": 240, "description": "Common first-line antibiotic for outpatient prescriptions."},
                {"name": "Azithromycin 500mg", "sku": "A-PH-004", "category": "Antibiotics", "unit_price": Decimal("64000"), "expiry_days": 210, "description": "Short-course antibiotic kept for respiratory infections."},
                {"name": "Amlodipine 5mg", "sku": "A-PH-005", "category": "Cardio & BP", "unit_price": Decimal("28000"), "expiry_days": 365, "description": "Daily antihypertensive used by regular chronic-care patients."},
                {"name": "Losartan 50mg", "sku": "A-PH-006", "category": "Cardio & BP", "unit_price": Decimal("46000"), "expiry_days": 340, "description": "ARB medicine with recurring refill demand."},
                {"name": "Metformin 850mg", "sku": "A-PH-007", "category": "Diabetes Care", "unit_price": Decimal("33000"), "expiry_days": 360, "description": "Routine diabetes therapy with stable monthly demand."},
            ],
            "inventory": {
                "A-PH-001": {"current": 165, "min": 45, "max": 260, "restocked_days_ago": 2},
                "A-PH-002": {"current": 92, "min": 28, "max": 170, "restocked_days_ago": 5},
                "A-PH-003": {"current": 54, "min": 22, "max": 120, "restocked_days_ago": 6},
                "A-PH-004": {"current": 10, "min": 16, "max": 70, "restocked_days_ago": 9},
                "A-PH-005": {"current": 128, "min": 36, "max": 220, "restocked_days_ago": 3},
                "A-PH-006": {"current": 14, "min": 20, "max": 85, "restocked_days_ago": 11},
                "A-PH-007": {"current": 73, "min": 24, "max": 140, "restocked_days_ago": 4},
            },
            "sales": [
                {"note": "ALPHA-2026-03-02-01", "days_ago": 10, "items": [("A-PH-001", 4), ("A-PH-005", 1)]},
                {"note": "ALPHA-2026-03-03-01", "days_ago": 9, "items": [("A-PH-003", 2), ("A-PH-001", 2)]},
                {"note": "ALPHA-2026-03-04-01", "days_ago": 8, "items": [("A-PH-006", 1), ("A-PH-005", 2)]},
                {"note": "ALPHA-2026-03-06-01", "days_ago": 6, "items": [("A-PH-001", 3), ("A-PH-002", 2)]},
                {"note": "ALPHA-2026-03-07-01", "days_ago": 5, "items": [("A-PH-004", 1), ("A-PH-003", 1), ("A-PH-001", 2)]},
                {"note": "ALPHA-2026-03-08-01", "days_ago": 4, "items": [("A-PH-007", 2), ("A-PH-005", 1)]},
                {"note": "ALPHA-2026-03-09-01", "days_ago": 3, "items": [("A-PH-001", 5), ("A-PH-002", 1)]},
                {"note": "ALPHA-2026-03-10-01", "days_ago": 2, "items": [("A-PH-006", 2), ("A-PH-005", 2)]},
                {"note": "ALPHA-2026-03-11-01", "days_ago": 1, "items": [("A-PH-003", 1), ("A-PH-001", 3), ("A-PH-007", 1)]},
            ],
            "reorders": [
                {"sku": "A-PH-004", "quantity": 48, "priority": "HIGH", "status": "PENDING", "reason": "Azithromycin stock fell below minimum after recent respiratory prescriptions."},
                {"sku": "A-PH-006", "quantity": 55, "priority": "URGENT", "status": "PENDING", "reason": "Losartan refill demand is ahead of schedule for chronic patients this week."},
            ],
        },
        "Pharmacy Beta": {
            "label": "BETA",
            "plan_type": Pharmacy.PlanType.BASIC,
            "admin": {
                "username": "beta",
                "email": "beta@pharmacyai.demo",
                "first_name": "Bekzod",
                "last_name": "Tursunov",
                "phone_number": "+998901110202",
            },
            "categories": [
                ("Cold & Flu", "Seasonal respiratory care for neighborhood walk-in patients."),
                ("Digestive Health", "Everyday stomach and gut symptom relief."),
                ("Vitamins & Immunity", "Supplement shelf focused on family wellness."),
                ("Child Care", "Frequent-use pediatric products and fever relief."),
            ],
            "medicines": [
                {"name": "Nasal Spray 15ml", "sku": "B-PH-001", "category": "Cold & Flu", "unit_price": Decimal("36000"), "expiry_days": 300, "description": "Fast-selling nasal spray during allergy and cold season."},
                {"name": "Cough Syrup 100ml", "sku": "B-PH-002", "category": "Cold & Flu", "unit_price": Decimal("29500"), "expiry_days": 210, "description": "Family-friendly cough syrup with frequent repeat sales."},
                {"name": "Omeprazole 20mg", "sku": "B-PH-003", "category": "Digestive Health", "unit_price": Decimal("34000"), "expiry_days": 260, "description": "Popular gastric-acid medicine for routine digestive complaints."},
                {"name": "Probiotic Capsules", "sku": "B-PH-004", "category": "Digestive Health", "unit_price": Decimal("81000"), "expiry_days": 320, "description": "Higher-margin digestive support product with slower but valuable turnover."},
                {"name": "Vitamin D3 2000 IU", "sku": "B-PH-005", "category": "Vitamins & Immunity", "unit_price": Decimal("45000"), "expiry_days": 365, "description": "Steady supplement product for adults and seniors."},
                {"name": "Zinc + C Effervescent", "sku": "B-PH-006", "category": "Vitamins & Immunity", "unit_price": Decimal("52000"), "expiry_days": 330, "description": "Immunity support SKU promoted during seasonal demand spikes."},
                {"name": "Children's Ibuprofen Suspension", "sku": "B-PH-007", "category": "Child Care", "unit_price": Decimal("47000"), "expiry_days": 270, "description": "Pediatric fever product with recurring household demand."},
            ],
            "inventory": {
                "B-PH-001": {"current": 58, "min": 20, "max": 125, "restocked_days_ago": 7},
                "B-PH-002": {"current": 134, "min": 40, "max": 220, "restocked_days_ago": 3},
                "B-PH-003": {"current": 46, "min": 18, "max": 110, "restocked_days_ago": 6},
                "B-PH-004": {"current": 9, "min": 14, "max": 60, "restocked_days_ago": 12},
                "B-PH-005": {"current": 118, "min": 35, "max": 210, "restocked_days_ago": 4},
                "B-PH-006": {"current": 39, "min": 16, "max": 90, "restocked_days_ago": 8},
                "B-PH-007": {"current": 11, "min": 18, "max": 75, "restocked_days_ago": 10},
            },
            "sales": [
                {"note": "BETA-2026-03-02-01", "days_ago": 10, "items": [("B-PH-002", 2), ("B-PH-005", 1)]},
                {"note": "BETA-2026-03-03-01", "days_ago": 9, "items": [("B-PH-001", 1), ("B-PH-003", 1)]},
                {"note": "BETA-2026-03-04-01", "days_ago": 8, "items": [("B-PH-007", 1), ("B-PH-002", 1)]},
                {"note": "BETA-2026-03-05-01", "days_ago": 7, "items": [("B-PH-006", 2), ("B-PH-005", 1)]},
                {"note": "BETA-2026-03-07-01", "days_ago": 5, "items": [("B-PH-004", 1), ("B-PH-003", 1)]},
                {"note": "BETA-2026-03-08-01", "days_ago": 4, "items": [("B-PH-002", 3), ("B-PH-001", 1)]},
                {"note": "BETA-2026-03-09-01", "days_ago": 3, "items": [("B-PH-005", 2), ("B-PH-006", 1)]},
                {"note": "BETA-2026-03-10-01", "days_ago": 2, "items": [("B-PH-007", 2), ("B-PH-002", 1)]},
                {"note": "BETA-2026-03-11-01", "days_ago": 1, "items": [("B-PH-003", 1), ("B-PH-002", 2), ("B-PH-005", 1)]},
            ],
            "reorders": [
                {"sku": "B-PH-004", "quantity": 36, "priority": "HIGH", "status": "PENDING", "reason": "Probiotic capsules are below safety stock after weekend demand."},
                {"sku": "B-PH-007", "quantity": 42, "priority": "HIGH", "status": "PENDING", "reason": "Pediatric ibuprofen is approaching stock-out during seasonal fever demand."},
            ],
        },
    }

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Resetting demo environment to Alpha, Beta, and superadmin only..."))

        self._reset_demo_scope()
        users = self._ensure_users()
        pharmacies = self._ensure_demo_pharmacies(users)

        for pharmacy_name, pharmacy in pharmacies.items():
            admin_user = users[self.BLUEPRINTS[pharmacy_name]["admin"]["username"]]
            self._seed_pharmacy_data(pharmacy, admin_user)

        self._run_consistency_checks()
        self.stdout.write(self.style.SUCCESS("Demo tenant seed completed successfully."))
        self._print_credentials()

    def _reset_demo_scope(self):
        SaleItem.objects.all().delete()
        Sale.objects.all().delete()
        ReorderRecommendation.objects.all().delete()
        Inventory.objects.all().delete()
        Medicine.objects.all().delete()
        Category.objects.all().delete()
        Pharmacy.objects.all().delete()
        User.objects.exclude(username__in=self.DEMO_USERNAMES).delete()
        User.objects.filter(username__in=self.DEMO_USERNAMES).update(pharmacy=None)
        self.stdout.write("Removed non-demo users and cleared all pharmacy tenant data.")

    def _ensure_users(self):
        superadmin, _ = User.objects.get_or_create(username="superadmin")
        superadmin.email = "superadmin@pharmacyai.demo"
        superadmin.first_name = "System"
        superadmin.last_name = "Owner"
        superadmin.phone_number = "+998901110000"
        superadmin.role = User.ROLE_ADMIN
        superadmin.is_staff = True
        superadmin.is_superuser = True
        superadmin.pharmacy = None
        superadmin.set_password(self.DEFAULT_PASSWORD)
        superadmin.save()

        users = {"superadmin": superadmin}
        for pharmacy_name, blueprint in self.BLUEPRINTS.items():
            admin_cfg = blueprint["admin"]
            user, _ = User.objects.get_or_create(username=admin_cfg["username"])
            user.email = admin_cfg["email"]
            user.first_name = admin_cfg["first_name"]
            user.last_name = admin_cfg["last_name"]
            user.phone_number = admin_cfg["phone_number"]
            user.role = User.ROLE_ADMIN
            user.is_staff = True
            user.is_superuser = False
            user.set_password(self.DEFAULT_PASSWORD)
            user.save()
            users[admin_cfg["username"]] = user

        self.stdout.write("Users ready: superadmin, alpha, beta")
        return users

    def _ensure_demo_pharmacies(self, users):
        pharmacies = {}
        for pharmacy_name, blueprint in self.BLUEPRINTS.items():
            owner = users[blueprint["admin"]["username"]]
            pharmacy, _ = Pharmacy.objects.get_or_create(
                name=pharmacy_name,
                defaults={"owner": owner, "plan_type": blueprint["plan_type"]},
            )
            pharmacy.owner = owner
            pharmacy.plan_type = blueprint["plan_type"]
            pharmacy.is_active = True
            pharmacy.subscription_start = timezone.now() - timedelta(days=14)
            pharmacy.subscription_end = timezone.now() + timedelta(days=76)
            pharmacy.apply_plan_limits()
            pharmacy.save()

            owner.pharmacy = pharmacy
            owner.save(update_fields=["pharmacy"])
            pharmacies[pharmacy_name] = pharmacy

        self.stdout.write("Pharmacies ready: Pharmacy Alpha, Pharmacy Beta")
        return pharmacies

    def _seed_pharmacy_data(self, pharmacy, admin_user):
        blueprint = self.BLUEPRINTS[pharmacy.name]
        categories = self._create_categories(pharmacy, blueprint["categories"])
        medicines = self._create_medicines(pharmacy, categories, blueprint["medicines"])
        self._create_inventory(pharmacy, medicines, blueprint["inventory"])
        self._create_sales(pharmacy, admin_user, medicines, blueprint["sales"])
        self._create_reorder_recommendations(pharmacy, admin_user, medicines, blueprint["reorders"])
        self.stdout.write(self.style.SUCCESS(f"Seeded realistic data for {pharmacy.name}"))

    def _create_categories(self, pharmacy, category_data):
        categories = {}
        for name, description in category_data:
            categories[name] = Category.objects.create(
                pharmacy=pharmacy,
                name=name,
                description=description,
            )
        return categories

    def _create_medicines(self, pharmacy, categories, medicine_data):
        medicines = {}
        for item in medicine_data:
            medicine = Medicine.objects.create(
                pharmacy=pharmacy,
                sku=item["sku"],
                name=item["name"],
                category=categories[item["category"]],
                description=item["description"],
                unit_price=item["unit_price"],
                expiry_date=timezone.localdate() + timedelta(days=item["expiry_days"]),
            )
            medicines[item["sku"]] = medicine
        return medicines

    def _create_inventory(self, pharmacy, medicines, stock_map):
        for sku, medicine in medicines.items():
            cfg = stock_map[sku]
            Inventory.objects.create(
                medicine=medicine,
                pharmacy=pharmacy,
                current_stock=cfg["current"],
                min_stock_level=cfg["min"],
                max_stock_level=cfg["max"],
                last_restocked_date=timezone.now() - timedelta(days=cfg["restocked_days_ago"]),
            )

    def _create_sales(self, pharmacy, admin_user, medicines, sales_blueprint):
        for idx, sale_cfg in enumerate(sales_blueprint, start=1):
            sale = Sale.objects.create(
                pharmacy=pharmacy,
                user=admin_user,
                notes=sale_cfg["note"],
                total_amount=Decimal("0.01"),
            )

            sale_date = timezone.make_aware(
                datetime.combine(
                    timezone.localdate() - timedelta(days=sale_cfg["days_ago"]),
                    time(hour=9 + (idx % 8), minute=10 + ((idx * 7) % 45)),
                ),
                timezone.get_current_timezone(),
            )
            Sale.objects.filter(pk=sale.pk).update(date=sale_date)

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

            sale.total_amount = total_amount if total_amount > 0 else Decimal("0.01")
            sale.save(update_fields=["total_amount", "updated_at"])

    def _create_reorder_recommendations(self, pharmacy, admin_user, medicines, reorder_blueprint):
        for offset, cfg in enumerate(reorder_blueprint, start=1):
            recommendation = ReorderRecommendation.objects.create(
                pharmacy=pharmacy,
                medicine=medicines[cfg["sku"]],
                recommended_quantity=cfg["quantity"],
                reason=cfg["reason"],
                priority=cfg["priority"],
                status=cfg["status"],
                approved_by=admin_user if cfg["status"] == "APPROVED" else None,
                approved_at=timezone.now() - timedelta(days=offset) if cfg["status"] == "APPROVED" else None,
            )
            if cfg["status"] == "PENDING":
                ReorderRecommendation.objects.filter(pk=recommendation.pk).update(
                    created_at=timezone.now() - timedelta(days=offset),
                    updated_at=timezone.now() - timedelta(days=offset),
                )

    def _run_consistency_checks(self):
        demo_ids = list(Pharmacy.objects.filter(name__in=self.DEMO_PHARMACIES).values_list("id", flat=True))

        if Pharmacy.objects.exclude(name__in=self.DEMO_PHARMACIES).exists():
            raise ValueError("Found pharmacies outside the approved demo scope.")

        if User.objects.exclude(username__in=self.DEMO_USERNAMES).exists():
            raise ValueError("Found users outside the approved demo scope.")

        mismatch_saleitems = SaleItem.objects.filter(pharmacy__id__in=demo_ids).exclude(pharmacy_id=models.F("sale__pharmacy_id")).count()
        if mismatch_saleitems:
            raise ValueError("Found SaleItem rows where SaleItem.pharmacy != Sale.pharmacy")

        mismatch_inventory = Inventory.objects.filter(pharmacy__id__in=demo_ids).exclude(pharmacy_id=models.F("medicine__pharmacy_id")).count()
        if mismatch_inventory:
            raise ValueError("Found Inventory rows where Inventory.pharmacy != Inventory.medicine.pharmacy")

        missing_inventory = Medicine.objects.filter(pharmacy__id__in=demo_ids, inventory__isnull=True).count()
        if missing_inventory:
            raise ValueError("Found demo medicines without inventory records.")

    def _print_credentials(self):
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo login credentials:"))
        self.stdout.write("  superadmin / DemoPass123! (superuser, all tenants)")
        self.stdout.write("  alpha      / DemoPass123! (Pharmacy Alpha)")
        self.stdout.write("  beta       / DemoPass123! (Pharmacy Beta)")
