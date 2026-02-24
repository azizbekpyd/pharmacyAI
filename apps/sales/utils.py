"""
Utility functions for sales analytics and reporting.

Helper functions for data aggregation, formatting, and report generation.
"""
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from .models import Sale, SaleItem


def format_currency(amount):
    """
    Format amount as currency string.
    
    Args:
        amount: Decimal or float amount
    
    Returns:
        str: Formatted currency string
    """
    return f"{float(amount):,.2f} UZS"


def format_percentage(value, total):
    """
    Calculate and format percentage.
    
    Args:
        value: Part value
        total: Total value
    
    Returns:
        dict: Percentage value and formatted string
    """
    if total == 0:
        return {'value': 0, 'formatted': '0.00%'}
    
    percentage = (value / total) * 100
    return {
        'value': round(percentage, 2),
        'formatted': f"{round(percentage, 2)}%"
    }


def get_date_range_periods(start_date, end_date, period='daily'):
    """
    Generate date range periods for aggregation.
    
    Args:
        start_date: Start date
        end_date: End date
        period: Period type - 'daily', 'weekly', 'monthly' (default: 'daily')
    
    Returns:
        list: List of period boundaries
    """
    periods = []
    current = start_date
    
    while current <= end_date:
        if period == 'daily':
            periods.append(current.date())
            current += timedelta(days=1)
        elif period == 'weekly':
            periods.append(current.date())
            current += timedelta(weeks=1)
        elif period == 'monthly':
            # Move to first day of next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1, day=1)
            else:
                current = current.replace(month=current.month + 1, day=1)
            periods.append(current.date())
    
    return periods


def calculate_sales_velocity(medicine_id, days=30):
    """
    Calculate sales velocity for a medicine.
    
    Sales velocity = total quantity sold / number of days
    
    Args:
        medicine_id: ID of the medicine
        days: Number of days to analyze
    
    Returns:
        float: Sales velocity (units per day)
    """
    start_date = timezone.now() - timedelta(days=days)
    
    total_quantity = (
        SaleItem.objects
        .filter(medicine_id=medicine_id, sale__date__gte=start_date)
        .aggregate(Sum('quantity'))['quantity__sum'] or 0
    )
    
    return total_quantity / days if days > 0 else 0


def get_top_performers(limit=10, days=30, metric='quantity'):
    """
    Get top performing medicines by specified metric.
    
    Args:
        limit: Number of results (default: 10)
        days: Number of days to analyze (default: 30)
        metric: Metric to rank by - 'quantity', 'revenue', 'frequency' (default: 'quantity')
    
    Returns:
        list: Top performing medicines
    """
    start_date = timezone.now() - timedelta(days=days)
    
    queryset = (
        SaleItem.objects
        .filter(sale__date__gte=start_date)
        .values('medicine__id', 'medicine__name', 'medicine__sku')
        .annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('subtotal'),
            sale_count=Count('sale', distinct=True)
        )
    )
    
    if metric == 'quantity':
        queryset = queryset.order_by('-total_quantity')
    elif metric == 'revenue':
        queryset = queryset.order_by('-total_revenue')
    elif metric == 'frequency':
        queryset = queryset.order_by('-sale_count')
    
    return list(queryset[:limit])


def calculate_inventory_turnover(medicine_id, days=30):
    """
    Calculate inventory turnover rate.
    
    Turnover = Cost of goods sold / Average inventory
    
    Note: This is a simplified calculation. In a real system,
    you would need cost data for accurate calculation.
    
    Args:
        medicine_id: ID of the medicine
        days: Number of days to analyze
    
    Returns:
        dict: Turnover metrics
    """
    start_date = timezone.now() - timedelta(days=days)
    
    # Get sales data
    sale_items = SaleItem.objects.filter(
        medicine_id=medicine_id,
        sale__date__gte=start_date
    )
    
    total_quantity_sold = sale_items.aggregate(Sum('quantity'))['quantity__sum'] or 0
    
    # Get average inventory (simplified - would need historical inventory snapshots)
    from apps.inventory.models import Inventory
    try:
        inventory = Inventory.objects.get(medicine_id=medicine_id)
        avg_inventory = inventory.current_stock  # Simplified
    except:
        avg_inventory = 0
    
    # Calculate turnover
    if avg_inventory > 0:
        turnover_rate = total_quantity_sold / avg_inventory
        days_to_sell = days / turnover_rate if turnover_rate > 0 else 0
    else:
        turnover_rate = 0
        days_to_sell = 0
    
    return {
        'medicine_id': medicine_id,
        'period_days': days,
        'total_quantity_sold': total_quantity_sold,
        'average_inventory': avg_inventory,
        'turnover_rate': round(turnover_rate, 2),
        'days_to_sell': round(days_to_sell, 2),
    }


def generate_sales_summary(start_date=None, end_date=None):
    """
    Generate comprehensive sales summary report.
    
    Args:
        start_date: Start date for report
        end_date: End date for report
    
    Returns:
        dict: Sales summary report
    """
    if not start_date:
        start_date = timezone.now() - timedelta(days=30)
    if not end_date:
        end_date = timezone.now()
    
    # Build date filter
    sales = Sale.objects.filter(date__gte=start_date, date__lte=end_date)
    
    # Basic metrics
    total_sales = sales.count()
    total_revenue = sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    avg_sale = sales.aggregate(Avg('total_amount'))['total_amount__avg'] or 0
    
    # Get top medicines
    top_medicines = get_top_performers(limit=5, days=(end_date - start_date).days)
    
    # Get sales by day of week
    daily_sales = (
        sales
        .extra(select={'day_of_week': "strftime('%%w', date)"})
        .values('day_of_week')
        .annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        )
        .order_by('day_of_week')
    )
    
    return {
        'period': {
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'days': (end_date - start_date).days
        },
        'summary': {
            'total_sales': total_sales,
            'total_revenue': float(total_revenue),
            'average_sale': float(avg_sale),
            'formatted_revenue': format_currency(total_revenue),
        },
        'top_medicines': top_medicines,
        'daily_breakdown': list(daily_sales),
    }
