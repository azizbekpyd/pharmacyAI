# Production Checklist

Use this before deploying Pharmacy Analytic AI outside local development.

## Environment

- Set `DJANGO_SETTINGS_MODULE=pharmacy_ai.settings_production`.
- Set a unique strong `SECRET_KEY`.
- Set `DEBUG=False`.
- Set `ALLOWED_HOSTS` to the real domain names only.
- Set `CSRF_TRUSTED_ORIGINS` to the HTTPS origins that serve the app.
- Keep `.env`, `db.sqlite3`, backups, and uploaded media out of Git.

## Database

- Use PostgreSQL for production.
- Configure `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, and `POSTGRES_SSLMODE`.
- Run `python manage.py migrate`.
- Create an admin account with `python manage.py createsuperuser`.
- Schedule automated PostgreSQL backups and test restore at least once.

## Static And Media

- Run `python manage.py collectstatic`.
- Serve `STATIC_ROOT` through the web server or platform static-file service.
- Store `MEDIA_ROOT` on persistent storage and back it up.

## Security

- Use HTTPS only.
- Enable secure cookies: `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, `LANGUAGE_COOKIE_SECURE=True`.
- Enable HSTS only after HTTPS is verified.
- Do not expose the demo database in production.
- Turn off demo mode and remove demo tenant credentials.

## Operations

- Verify owner/admin/pharmacist/cashier roles before giving users access.
- Confirm CSV import/export access is limited to trusted staff.
- Review the audit log after first live workflows: medicine edit, sale, stock adjustment, purchase receive.
- Confirm stock movement ledger entries are generated for sales, purchases, and manual adjustments.
- Check expiry/low-stock dashboard counts after importing real medicines.
