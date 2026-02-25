"""
API views for POS integration app.

Handles POS data ingestion via REST API and CSV import.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
import csv
import io
from .serializers import POSSaleSerializer, POSBulkSaleSerializer
from apps.sales.models import Sale, SaleItem
from apps.medicines.models import Medicine
from apps.tenants.models import Pharmacy
from apps.tenants.services import SubscriptionService
from apps.tenants.utils import require_user_pharmacy


def _resolve_request_pharmacy(request):
    user = request.user
    if user.is_superuser:
        pharmacy_id = request.data.get("pharmacy") or request.query_params.get("pharmacy_id")
        if not pharmacy_id:
            return None
        return Pharmacy.objects.filter(id=pharmacy_id).first()
    return require_user_pharmacy(user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Can be changed to AllowAny with API key authentication
def receive_sale(request):
    """
    Receive a single sale from POS system.
    
    Request body format:
    {
        "sale_id": "POS-12345",
        "date": "2024-01-15T10:30:00Z",
        "items": [
            {
                "medicine_sku": "MED001",
                "quantity": 2,
                "unit_price": 10.50
            }
        ],
        "notes": "Optional notes"
    }
    """
    pharmacy = _resolve_request_pharmacy(request)
    if request.user.is_superuser and pharmacy is None:
        return Response(
            {'error': 'pharmacy or pharmacy_id is required for superuser requests'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = POSSaleSerializer(data=request.data, context={'user': request.user, 'pharmacy': pharmacy})
    
    if serializer.is_valid():
        sale = serializer.save()
        return Response({
            'message': 'Sale received successfully',
            'sale_id': sale.id,
            'total_amount': float(sale.total_amount)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_bulk_sales(request):
    """
    Receive multiple sales from POS system in bulk.
    
    Request body format:
    {
        "sales": [
            {
                "sale_id": "POS-12345",
                "date": "2024-01-15T10:30:00Z",
                "items": [...]
            },
            ...
        ]
    }
    """
    pharmacy = _resolve_request_pharmacy(request)
    if request.user.is_superuser and pharmacy is None:
        return Response(
            {'error': 'pharmacy or pharmacy_id is required for superuser requests'},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer = POSBulkSaleSerializer(data=request.data, context={'user': request.user, 'pharmacy': pharmacy})
    
    if serializer.is_valid():
        sales = serializer.save()
        return Response({
            'message': f'{len(sales)} sales received successfully',
            'count': len(sales),
            'sales': [{'id': sale.id, 'total_amount': float(sale.total_amount)} for sale in sales]
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_csv_sales(request):
    """
    Import sales data from CSV file.
    
    CSV format:
    date,medicine_sku,quantity,unit_price,notes
    
    Example:
    2024-01-15 10:30:00,MED001,2,10.50,First sale
    2024-01-15 11:00:00,MED002,1,25.00,Second sale
    
    Note: Each row creates a separate sale with one item.
    """
    pharmacy = _resolve_request_pharmacy(request)
    if request.user.is_superuser and pharmacy is None:
        return Response(
            {'error': 'pharmacy or pharmacy_id is required for superuser requests'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if 'file' not in request.FILES:
        return Response(
            {'error': 'CSV file is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    csv_file = request.FILES['file']
    
    # Read CSV file
    try:
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
    except Exception as e:
        return Response(
            {'error': f'Error reading CSV file: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    created_sales = []
    errors = []
    
    for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
        try:
            # Parse date
            sale_date = timezone.now()
            if 'date' in row and row['date']:
                try:
                    from datetime import datetime
                    sale_date = datetime.strptime(row['date'], '%Y-%m-%d %H:%M:%S')
                    sale_date = timezone.make_aware(sale_date)
                except:
                    pass  # Use current time if parsing fails
            
            # Get medicine
            medicine_sku = row.get('medicine_sku', '').strip()
            if not medicine_sku:
                errors.append(f'Row {row_num}: medicine_sku is required')
                continue
            
            try:
                medicine = Medicine.objects.get(sku=medicine_sku, pharmacy=pharmacy)
            except Medicine.DoesNotExist:
                errors.append(f'Row {row_num}: Medicine with SKU "{medicine_sku}" not found')
                continue
            
            # Get quantity and price
            quantity = int(row.get('quantity', 1))
            unit_price = float(row.get('unit_price', medicine.unit_price))
            notes = row.get('notes', '')
            
            # Create sale
            if not request.user.is_superuser:
                try:
                    SubscriptionService.enforce_limits(pharmacy, SubscriptionService.RESOURCE_MONTHLY_SALES)
                except DjangoValidationError as exc:
                    if hasattr(exc, "message_dict"):
                        limit_message = str(exc.message_dict)
                    else:
                        limit_message = ", ".join(exc.messages)
                    errors.append(f'Row {row_num}: {limit_message}')
                    continue

            sale = Sale.objects.create(
                date=sale_date,
                user=request.user,
                pharmacy=pharmacy,
                notes=notes,
                total_amount=0  # Will be updated
            )
            
            # Create sale item
            sale_item = SaleItem.objects.create(
                sale=sale,
                pharmacy=pharmacy,
                medicine=medicine,
                quantity=quantity,
                unit_price=unit_price
            )
            
            # Update sale total
            sale.total_amount = sale_item.subtotal
            sale.save()
            
            # Update inventory
            try:
                inventory = medicine.inventory
                inventory.current_stock -= quantity
                if inventory.current_stock < 0:
                    inventory.current_stock = 0
                inventory.save()
            except:
                pass  # Inventory might not exist
            
            created_sales.append({
                'id': sale.id,
                'date': sale.date.isoformat(),
                'total_amount': float(sale.total_amount)
            })
            
        except Exception as e:
            errors.append(f'Row {row_num}: {str(e)}')
    
    return Response({
        'message': f'Imported {len(created_sales)} sales',
        'created': len(created_sales),
        'errors': errors,
        'sales': created_sales
    }, status=status.HTTP_201_CREATED if created_sales else status.HTTP_400_BAD_REQUEST)
