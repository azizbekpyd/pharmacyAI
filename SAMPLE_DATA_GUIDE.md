# Sample Data Generation Guide

## Overview

The `create_sample_data` management command generates comprehensive test data for the Pharmacy Analytic AI project, including users, medicines, inventory, and sales records.

## Command Location

The management command is located at:
```
apps/dashboard/management/commands/create_sample_data.py
```

## How to Run

### Basic Usage

```bash
python manage.py create_sample_data
```

This will create all sample data without clearing existing data.

### Clear Existing Data First

To clear existing data before creating sample data:

```bash
python manage.py create_sample_data --clear
```

**Warning**: The `--clear` flag will delete:
- All sales and sale items
- All inventory records
- All medicines
- All categories
- All non-superuser users

## What Gets Created

### 1. Users (2 users)

**Admin User:**
- Email: `admin@gmail.com`
- Username: `admin`
- Password: `12345`
- Role: Admin (is_staff=True, is_superuser=True)

**Pharmacy Manager:**
- Email: `manager@gmail.com`
- Username: `manager`
- Password: `12345`
- Role: Pharmacy Manager

### 2. Categories (6 categories)

- Antibiotics
- Pain Relief
- Vitamins & Supplements
- Cold & Flu
- Digestive Health
- Skin Care

### 3. Medicines (10 medicines)

Each medicine includes:
- Name, SKU, Category
- Unit price (varies)
- Expiry date (some expiring soon, some safe)

**Sample medicines:**
- Paracetamol 500mg (MED001)
- Amoxicillin 250mg (MED002)
- Vitamin C 1000mg (MED003) - Expiring soon
- Ibuprofen 400mg (MED004)
- Cough Syrup 100ml (MED005) - Expiring soon
- Antacid Tablets (MED006)
- Multivitamin Complex (MED007)
- Antibacterial Cream (MED008) - Expiring soon
- Aspirin 100mg (MED009)
- Probiotics Capsules (MED010)

### 4. Inventory (10 records)

Each medicine gets an inventory record with:
- Current stock (varies: 3-70 units)
- Minimum stock level (15-30 units)
- Maximum stock level (100 units)

**Stock Status:**
- **Low Stock** (needs reorder): 5 medicines
- **Normal Stock**: 3 medicines
- **Good Stock**: 2 medicines

### 5. Sales Data (Last 30 Days)

- **Total Sales**: Approximately 100-200 sales records
- **Time Period**: Last 30 days
- **Sales per Day**: 1-8 sales randomly distributed
- **Items per Sale**: 1-4 items

**Fast-Moving Medicines** (sell frequently):
- Paracetamol (MED001)
- Ibuprofen (MED004)
- Antacid (MED006)
- Aspirin (MED009)

**Slow-Moving Medicines** (sell rarely):
- Antibacterial Cream (MED008)
- Probiotics (MED010)

## Features

### Realistic Data
- Sales distributed across business hours (9 AM - 6 PM)
- Varying quantities based on medicine type
- Inventory automatically updated when sales are created
- Some medicines expiring soon (within 30 days)
- Mix of low, normal, and good stock levels

### Safe Execution
- Uses `get_or_create()` to avoid duplicates
- Won't overwrite existing data unless `--clear` is used
- Passwords are properly hashed using Django's `set_password()`

## Example Output

When you run the command, you'll see:

```
Starting to create sample data...
Creating users...
  ✓ Created admin user: admin@gmail.com
  ✓ Created manager user: manager@gmail.com
Creating categories...
  ✓ Created category: Antibiotics
  ✓ Created category: Pain Relief
  ...
Creating medicines...
  ✓ Created medicine: Paracetamol 500mg
  ...
Creating inventory records...
  ✓ Created inventory for Paracetamol 500mg: 5 units (LOW)
  ...
Creating sales data for the last 30 days...
  ✓ Created 156 sales records
  ✓ Fast-moving medicines: MED001, MED004, MED006, MED009
  ✓ Slow-moving medicines: MED008, MED010

✅ Sample data created successfully!

Login credentials:
  Admin: admin@gmail.com / 12345
  Manager: manager@gmail.com / 12345
```

## Testing the Data

After running the command, you can:

1. **Login to Dashboard:**
   - Visit `http://localhost:8000/login/`
   - Use `admin@gmail.com` / `12345`

2. **View Dashboard:**
   - See sales statistics
   - View fast/slow moving medicines
   - Check inventory alerts

3. **Test Analytics:**
   - Go to Sales Analytics page
   - View charts and trends
   - Check forecasting

4. **Test Inventory:**
   - View inventory list
   - Check reorder recommendations
   - See low stock alerts

5. **Test Medicines:**
   - View medicines list
   - Filter by expiring soon
   - Check stock levels

## Troubleshooting

### Command Not Found
If you get "Unknown command: create_sample_data":
- Make sure the file is in `apps/dashboard/management/commands/`
- Check that `apps.dashboard` is in `INSTALLED_APPS`
- Run `python manage.py help` to see available commands

### Duplicate Data
If you see warnings about existing data:
- Use `--clear` flag to remove existing data first
- Or manually delete data via Django admin

### Sales Not Showing
- Make sure users were created successfully
- Check that medicines and inventory exist
- Verify date ranges in sales queries

## Customization

To customize the sample data:

1. **Edit Medicine List:**
   - Modify `medicines_data` list in `create_medicines()` method

2. **Change Stock Levels:**
   - Modify `stock_configs` in `create_inventory()` method

3. **Adjust Sales Frequency:**
   - Modify `num_sales_today` range in `create_sales_data()` method
   - Change fast/slow moving medicine SKUs

4. **Change Time Period:**
   - Modify `timedelta(days=30)` in `create_sales_data()` method

## Notes

- The command is idempotent (safe to run multiple times)
- Existing data won't be overwritten unless `--clear` is used
- Sales data includes realistic patterns (more sales for fast-moving medicines)
- Inventory is automatically decremented when sales are created
- All dates are relative to the current date
