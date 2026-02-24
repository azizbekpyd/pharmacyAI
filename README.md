# Pharmacy Analytic AI

Django-based pharmacy analytics platform with inventory tracking, sales analytics, and multi-tenant support.

## Stack

- Python + Django
- Django REST Framework
- SQLite (default development database)

## Project Structure

```text
pharmacyAI-curs/
  apps/                 # Django applications
  pharmacy_ai/          # Django project settings and URL config
  templates/            # HTML templates
  static/               # Static assets
  manage.py
  requirements.txt
```

## Quick Start

1. Create and activate a virtual environment.

```powershell
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Create local environment file.

```powershell
Copy-Item .env.example .env
```

4. Run migrations and start the server.

```powershell
python manage.py migrate
python manage.py runserver
```

5. Open the app at `http://127.0.0.1:8000/`.

## Useful Commands

```powershell
python manage.py createsuperuser
python manage.py check
python manage.py seed_demo_tenants
```

## Additional Documentation

- `SETUP_GUIDE.md`
- `API_DOCUMENTATION.md`
- `ANALYTICS_FORECASTING.md`
- `FRONTEND_DASHBOARD.md`
- `SAMPLE_DATA_GUIDE.md`
- `SALES_ANALYTICS_CONTEXT.md`

## GitHub Publish Checklist

This repository is configured to keep local/development data out of source control:

- Virtual environments are ignored (`venv/`, `.venv/`)
- Local secrets are ignored (`.env`)
- Local SQLite files are ignored (`db.sqlite3`, `*.sqlite3`)
- Generated static/media folders are ignored

### First Push Example

```powershell
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```
