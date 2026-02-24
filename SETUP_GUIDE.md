# Pharmacy Analytic AI - Setup Guide

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update if needed:

```bash
cp .env.example .env
```

### 3. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser

```bash
python manage.py createsuperuser
```

Follow the prompts to create an admin user.

### 5. Run Development Server

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Access Points

- **Frontend Dashboard**: `http://localhost:8000/`
- **Login Page**: `http://localhost:8000/login/`
- **Admin Panel**: `http://localhost:8000/admin/`
- **API Root**: `http://localhost:8000/api/`

## Default Login Credentials

After creating a superuser, you can login with:
- **Username**: (your created username)
- **Password**: (your created password)

Or create a test user via admin panel or API.

## Project Structure

```
pharmacyAI-curs/
├── apps/                    # Django applications
│   ├── accounts/           # User authentication
│   ├── medicines/          # Medicine management
│   ├── sales/              # Sales & analytics
│   ├── inventory/         # Inventory management
│   ├── pos_integration/    # POS system integration
│   └── dashboard/          # Dashboard views
├── templates/              # HTML templates
├── static/                 # Static files (CSS, JS)
├── pharmacy_ai/            # Main Django project
└── manage.py               # Django management script
```

## Features Overview

### ✅ Completed Features

1. **User Authentication**
   - Login/Logout
   - Role-based access (Admin/Pharmacy Manager)
   - Session management

2. **Medicines Management**
   - CRUD operations
   - Category management
   - Expiry date tracking
   - Stock level monitoring

3. **Sales Management**
   - Sales records
   - Sales analytics
   - Fast/slow moving medicines
   - Demand forecasting

4. **Inventory Management**
   - Stock monitoring
   - Automatic reorder recommendations
   - Low stock alerts

5. **POS Integration**
   - REST API endpoints
   - CSV import
   - Bulk sales ingestion

6. **Dashboard**
   - Overview with key metrics
   - Charts and visualizations
   - Real-time data updates

## API Documentation

See `API_DOCUMENTATION.md` for complete API reference.

## Analytics & Forecasting

See `ANALYTICS_FORECASTING.md` for detailed analytics documentation.

## Frontend Dashboard

See `FRONTEND_DASHBOARD.md` for frontend documentation.

## Testing the Application

### 1. Create Sample Data

Use Django admin panel or API to create:
- Categories
- Medicines
- Inventory records
- Sales (or import via POS)

### 2. Test Features

1. **Login**: Test authentication
2. **Dashboard**: View overview metrics
3. **Medicines**: Add/edit medicines
4. **Sales**: Create sales records
5. **Analytics**: View sales analytics
6. **Inventory**: Check stock levels
7. **Reorder**: Generate recommendations

## Troubleshooting

### Common Issues

1. **Migration Errors**
   ```bash
   python manage.py makemigrations
   python manage.py migrate --run-syncdb
   ```

2. **Static Files Not Loading**
   ```bash
   python manage.py collectstatic
   ```

3. **CSRF Errors**
   - Ensure CSRF middleware is enabled
   - Check CSRF token in forms

4. **API Not Working**
   - Check authentication
   - Verify API endpoints
   - Check CORS settings

## Development Tips

1. **Enable Debug Mode**: Set `DEBUG=True` in settings
2. **Use SQLite**: Default database (good for development)
3. **Check Logs**: Django console output for errors
4. **API Testing**: Use browser DevTools or Postman

## Next Steps

1. Add sample data for testing
2. Customize dashboard widgets
3. Add more analytics features
4. Integrate with actual POS system
5. Deploy to production server

## Support

For issues or questions:
- Check documentation files
- Review code comments
- Test with sample data
- Check Django console for errors

## License

University Diploma Project - Pharmacy Analytic AI
