"""
URL configuration for POS integration app.
"""
from django.urls import path
from .views import receive_sale, receive_bulk_sales, import_csv_sales

app_name = 'pos_integration'

urlpatterns = [
    path('sales/', receive_sale, name='receive-sale'),
    path('sales/bulk/', receive_bulk_sales, name='receive-bulk-sales'),
    path('import-csv/', import_csv_sales, name='import-csv-sales'),
]
