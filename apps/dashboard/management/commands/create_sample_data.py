"""
Django management command to create sample test data.

This command generates sample data for development and demo purposes:
- Sample users (admin and pharmacy manager)
- Sample medicines with categories
- Sample inventory records
- Sample sales data for the last 30 days

Usage:
    python manage.py create_sample_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
import random

from apps.accounts.models import User
from apps.tenants.models import Pharmacy
from apps.medicines.models import Category, Medicine
from apps.inventory.models import Inventory
from apps.sales.models import Sale, SaleItem


class Command(BaseCommand):
    help = 'Creates sample test data for Pharmacy Analytic AI'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before creating sample data',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to create sample data...'))
        
        # Clear existing data if requested
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            SaleItem.objects.all().delete()
            Sale.objects.all().delete()
            Inventory.objects.all().delete()
            Medicine.objects.all().delete()
            Category.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()
            self.stdout.write(self.style.SUCCESS('Existing data cleared.'))

        # Create users
        admin, manager = self.create_users()
        pharmacy = self.ensure_default_pharmacy(admin, manager)
        
        # Create categories
        categories = self.create_categories(pharmacy)
        
        # Create medicines
        medicines = self.create_medicines(categories, pharmacy)
        
        # Create inventory
        self.create_inventory(medicines, pharmacy)
        
        # Create sales data
        self.create_sales_data(medicines, pharmacy)
        
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Sample data created successfully!'))
        self.stdout.write(self.style.SUCCESS('\nLogin credentials:'))
        self.stdout.write(self.style.SUCCESS('  Admin: admin@gmail.com / 12345'))
        self.stdout.write(self.style.SUCCESS('  Manager: manager@gmail.com / 12345'))

    def create_users(self):
        """Create sample users: admin and pharmacy manager."""
        self.stdout.write('Creating users...')
        
        # Create admin user
        admin, created = User.objects.get_or_create(
            email='admin@gmail.com',
            defaults={
                'username': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'role': 'ADMIN',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created or not admin.check_password('12345'):
            admin.set_password('12345')
            admin.save()
            self.stdout.write(self.style.SUCCESS(f'  [OK] Created admin user: {admin.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'  [-] Admin user already exists: {admin.email}'))
        
        # Create pharmacy manager user
        manager, created = User.objects.get_or_create(
            email='manager@gmail.com',
            defaults={
                'username': 'manager',
                'first_name': 'Pharmacy',
                'last_name': 'Manager',
                'role': 'PHARMACY_MANAGER',
            }
        )
        if created or not manager.check_password('12345'):
            manager.set_password('12345')
            manager.save()
            self.stdout.write(self.style.SUCCESS(f'  [OK] Created manager user: {manager.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'  [-] Manager user already exists: {manager.email}'))

        return admin, manager

    def ensure_default_pharmacy(self, admin, manager):
        pharmacy, _ = Pharmacy.objects.get_or_create(
            name="Default Pharmacy",
            defaults={
                "owner": admin,
                "plan_type": Pharmacy.PlanType.BASIC,
            },
        )
        if pharmacy.owner_id != admin.id:
            pharmacy.owner = admin
            pharmacy.save(update_fields=["owner"])

        if admin.pharmacy_id != pharmacy.id:
            admin.pharmacy = pharmacy
            admin.save(update_fields=["pharmacy"])
        if manager.pharmacy_id != pharmacy.id:
            manager.pharmacy = pharmacy
            manager.save(update_fields=["pharmacy"])

        return pharmacy

    def create_categories(self, pharmacy):
        """Create medicine categories."""
        self.stdout.write('Creating categories...')
        
        categories_data = [
            'Antibiotics',
            'Pain Relief',
            'Vitamins & Supplements',
            'Cold & Flu',
            'Digestive Health',
            'Skin Care',
        ]
        
        categories = []
        for cat_name in categories_data:
            category, created = Category.objects.get_or_create(name=cat_name, pharmacy=pharmacy)
            categories.append(category)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Created category: {cat_name}'))
        
        return categories

    def create_medicines(self, categories, pharmacy):
        """Create sample medicines with various properties."""
        self.stdout.write('Creating medicines...')
        
        # Sample medicines data
        medicines_data = [
            {
                'name': 'Paracetamol 500mg',
                'sku': 'MED001',
                'category': 'Pain Relief',
                'unit_price': 12000,
                'expiry_date': date.today() + timedelta(days=180),  # Safe expiry
            },
            {
                'name': 'Amoxicillin 250mg',
                'sku': 'MED002',
                'category': 'Antibiotics',
                'unit_price': 38000,
                'expiry_date': date.today() + timedelta(days=90),  # Safe expiry
            },
            {
                'name': 'Vitamin C 1000mg',
                'sku': 'MED003',
                'category': 'Vitamins & Supplements',
                'unit_price': 22000,
                'expiry_date': date.today() + timedelta(days=25),  # Expiring soon
            },
            {
                'name': 'Ibuprofen 400mg',
                'sku': 'MED004',
                'category': 'Pain Relief',
                'unit_price': 18000,
                'expiry_date': date.today() + timedelta(days=200),  # Safe expiry
            },
            {
                'name': 'Cough Syrup 100ml',
                'sku': 'MED005',
                'category': 'Cold & Flu',
                'unit_price': 26000,
                'expiry_date': date.today() + timedelta(days=15),  # Expiring soon
            },
            {
                'name': 'Antacid Tablets',
                'sku': 'MED006',
                'category': 'Digestive Health',
                'unit_price': 9500,
                'expiry_date': date.today() + timedelta(days=300),  # Safe expiry
            },
            {
                'name': 'Multivitamin Complex',
                'sku': 'MED007',
                'category': 'Vitamins & Supplements',
                'unit_price': 64000,
                'expiry_date': date.today() + timedelta(days=120),  # Safe expiry
            },
            {
                'name': 'Antibacterial Cream',
                'sku': 'MED008',
                'category': 'Skin Care',
                'unit_price': 28500,
                'expiry_date': date.today() + timedelta(days=10),  # Expiring soon
            },
            {
                'name': 'Aspirin 100mg',
                'sku': 'MED009',
                'category': 'Pain Relief',
                'unit_price': 8000,
                'expiry_date': date.today() + timedelta(days=250),  # Safe expiry
            },
            {
                'name': 'Probiotics Capsules',
                'sku': 'MED010',
                'category': 'Digestive Health',
                'unit_price': 78000,
                'expiry_date': date.today() + timedelta(days=60),  # Safe expiry
            },
        ]
        
        medicines = []
        for med_data in medicines_data:
            # Find category
            category = next((c for c in categories if c.name == med_data['category']), categories[0])
            
            medicine, created = Medicine.objects.get_or_create(
                sku=med_data['sku'],
                pharmacy=pharmacy,
                defaults={
                    'name': med_data['name'],
                    'category': category,
                    'pharmacy': pharmacy,
                    'unit_price': med_data['unit_price'],
                    'expiry_date': med_data['expiry_date'],
                    'description': f'Sample {med_data["name"]} medicine for testing purposes.',
                }
            )
            medicines.append(medicine)
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Created medicine: {med_data["name"]}'))
        
        return medicines

    def create_inventory(self, medicines, pharmacy):
        """Create inventory records for medicines with varying stock levels."""
        self.stdout.write('Creating inventory records...')
        
        # Define stock levels: (current_stock, min_stock_level, max_stock_level)
        # Some medicines will be low stock, some normal, some slow-moving
        stock_configs = [
            (5, 10, 100),   # Low stock - needs reorder
            (25, 20, 100),  # Normal stock
            (50, 30, 100),  # Good stock
            (3, 15, 100),   # Very low stock - urgent
            (40, 25, 100),  # Normal stock
            (60, 20, 100),  # Good stock
            (8, 20, 100),   # Low stock
            (35, 30, 100),  # Normal stock
            (70, 15, 100), # Good stock
            (12, 25, 100),  # Low stock
        ]
        
        for i, medicine in enumerate(medicines):
            current_stock, min_stock, max_stock = stock_configs[i % len(stock_configs)]
            
            inventory, created = Inventory.objects.get_or_create(
                medicine=medicine,
                pharmacy=pharmacy,
                defaults={
                    'pharmacy': pharmacy,
                    'current_stock': current_stock,
                    'min_stock_level': min_stock,
                    'max_stock_level': max_stock,
                    'last_restocked_date': timezone.now() - timedelta(days=random.randint(1, 30)),
                }
            )
            if created:
                status = 'LOW' if current_stock < min_stock else 'NORMAL'
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK] Created inventory for {medicine.name}: {current_stock} units ({status})'
                ))

    def create_sales_data(self, medicines, pharmacy):
        """Create sales records for the last 30 days."""
        self.stdout.write('Creating sales data for the last 30 days...')
        
        # Get users for sales
        admin = User.objects.filter(email='admin@gmail.com').first()
        manager = User.objects.filter(email='manager@gmail.com').first()
        users = [admin, manager] if admin and manager else [admin] if admin else []
        
        if not users:
            self.stdout.write(self.style.ERROR('  ✗ No users found. Cannot create sales.'))
            return
        
        # Define which medicines sell fast (high frequency) and slow (low frequency)
        # Fast-moving: Paracetamol, Ibuprofen, Aspirin, Antacid
        fast_moving_skus = ['MED001', 'MED004', 'MED006', 'MED009']
        # Slow-moving: Antibacterial Cream, Probiotics
        slow_moving_skus = ['MED008', 'MED010']
        
        total_sales = 0
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Generate sales for each day in the last 30 days
        current_date = start_date
        while current_date <= end_date:
            # Random number of sales per day (1-8 sales)
            num_sales_today = random.randint(1, 8)
            
            for _ in range(num_sales_today):
                # Create a sale
                sale = Sale.objects.create(
                    date=current_date + timedelta(hours=random.randint(9, 18)),  # Business hours
                    user=random.choice(users),
                    pharmacy=pharmacy,
                    total_amount=0,  # Will be calculated
                    notes=f'Sample sale on {current_date.date()}'
                )
                
                # Add 1-4 items to each sale
                num_items = random.randint(1, 4)
                sale_total = 0
                
                for _ in range(num_items):
                    # Select medicine (weighted towards fast-moving)
                    if random.random() < 0.6:  # 60% chance for fast-moving
                        medicine = next((m for m in medicines if m.sku in fast_moving_skus), medicines[0])
                    elif random.random() < 0.2:  # 20% chance for slow-moving
                        medicine = next((m for m in medicines if m.sku in slow_moving_skus), medicines[0])
                    else:  # 20% chance for any other
                        medicine = random.choice(medicines)
                    
                    # Quantity (more for fast-moving)
                    if medicine.sku in fast_moving_skus:
                        quantity = random.randint(2, 5)
                    elif medicine.sku in slow_moving_skus:
                        quantity = random.randint(1, 2)
                    else:
                        quantity = random.randint(1, 3)
                    
                    # Create sale item
                    sale_item = SaleItem.objects.create(
                        sale=sale,
                        pharmacy=pharmacy,
                        medicine=medicine,
                        quantity=quantity,
                        unit_price=medicine.unit_price
                    )
                    
                    sale_total += sale_item.subtotal
                    
                    # Update inventory (subtract sold quantity)
                    try:
                        inventory = medicine.inventory
                        inventory.current_stock = max(0, inventory.current_stock - quantity)
                        inventory.save()
                    except:
                        pass  # Inventory might not exist
                
                # Update sale total
                sale.total_amount = sale_total
                sale.save()
                total_sales += 1
            
            # Move to next day
            current_date += timedelta(days=1)
        
        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {total_sales} sales records'))
        self.stdout.write(self.style.SUCCESS(f'  [OK] Fast-moving medicines: {", ".join(fast_moving_skus)}'))
        self.stdout.write(self.style.SUCCESS(f'  [OK] Slow-moving medicines: {", ".join(slow_moving_skus)}'))
