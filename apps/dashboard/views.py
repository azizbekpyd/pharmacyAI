"""
Template views for dashboard app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F, Sum
from django.utils import timezone
from datetime import timedelta
import json

from apps.sales.models import Sale, SaleItem
from apps.medicines.models import Medicine
from apps.inventory.models import Inventory, ReorderRecommendation


def _scope_queryset(queryset, pharmacy):
    if pharmacy is None:
        return queryset
    return queryset.filter(pharmacy=pharmacy)


@login_required
def dashboard_view(request):
    """
    Render the main dashboard page with real analytics data.

    Context keys (used by `templates/dashboard/index.html`):
    - total_sales, total_revenue_uzs
    - sales_growth_pct, revenue_growth_pct
    - trend_labels_json, trend_sales_json, trend_revenue_json
    - category_labels_json, category_revenue_json
    - fast_moving_medicines, slow_moving_medicines
    - medicines_count, expiring_soon_count, low_stock_count
    """
    now = timezone.now()
    pharmacy = None if request.user.is_superuser else request.pharmacy

    # Summary (last 30 days)
    start_30 = now - timedelta(days=30)
    sales_30 = _scope_queryset(Sale.objects.filter(date__gte=start_30), pharmacy)
    total_sales = sales_30.count()
    total_revenue = float(sales_30.aggregate(total=Sum('total_amount'))['total'] or 0)

    # Growth vs previous 30 days (simple)
    prev_30_start = start_30 - timedelta(days=30)
    prev_sales = _scope_queryset(
        Sale.objects.filter(date__gte=prev_30_start, date__lt=start_30),
        pharmacy,
    )
    prev_count = prev_sales.count()
    prev_revenue = float(prev_sales.aggregate(total=Sum('total_amount'))['total'] or 0)

    sales_growth_pct = None
    if prev_count > 0:
        sales_growth_pct = ((total_sales - prev_count) / prev_count) * 100

    revenue_growth_pct = None
    if prev_revenue > 0:
        revenue_growth_pct = ((total_revenue - prev_revenue) / prev_revenue) * 100

    # Sales trend (last 7 days, grouped by date)
    start_7 = now - timedelta(days=7)
    trend_qs = (
        _scope_queryset(Sale.objects, pharmacy)
        .filter(date__gte=start_7)
        .extra(select={'day': "date(date)"})
        .values('day')
        .annotate(total_sales=Count('id'), total_amount=Sum('total_amount'))
        .order_by('day')
    )
    trend_labels = []
    trend_sales = []
    trend_revenue = []
    for row in trend_qs:
        day_str = str(row['day'])
        trend_labels.append(day_str)
        trend_sales.append(int(row.get('total_sales') or 0))
        trend_revenue.append(float(row.get('total_amount') or 0))

    # Category distribution (last 30 days, by revenue)
    category_qs = (
        _scope_queryset(SaleItem.objects, pharmacy)
        .filter(sale__date__gte=start_30)
        .values('medicine__category__name')
        .annotate(total_revenue=Sum('subtotal'))
        .order_by('-total_revenue')
    )
    category_labels = []
    category_revenue = []
    for row in category_qs:
        category_labels.append(row.get('medicine__category__name') or 'Uncategorized')
        category_revenue.append(float(row.get('total_revenue') or 0))

    # Fast moving medicines (last 30 days, top 5 by quantity)
    fast_moving = list(
        _scope_queryset(SaleItem.objects, pharmacy)
        .filter(sale__date__gte=start_30)
        .values('medicine__id', 'medicine__name', 'medicine__sku')
        .annotate(total_quantity=Sum('quantity'), total_revenue=Sum('subtotal'))
        .order_by('-total_quantity')[:5]
    )
    for item in fast_moving:
        item['medicine__id'] = int(item.get('medicine__id') or 0)
        item['total_quantity'] = int(item.get('total_quantity') or 0)
        item['total_revenue'] = float(item.get('total_revenue') or 0)
        item['total_revenue_uzs'] = item['total_revenue']

    # Slow moving medicines (last 90 days, low/no sales; show 5)
    start_90 = now - timedelta(days=90)
    sold_ids = set(
        _scope_queryset(SaleItem.objects, pharmacy)
        .filter(sale__date__gte=start_90)
        .values_list('medicine_id', flat=True)
        .distinct()
    )
    slow_moving = []
    for medicine in _scope_queryset(Medicine.objects, pharmacy).all():
        if medicine.id not in sold_ids:
                slow_moving.append({
                    'medicine_id': int(medicine.id),
                    'medicine_name': medicine.name,
                    'medicine_sku': medicine.sku,
                    'total_quantity': 0,
                    'total_revenue_uzs': 0.0,
                })
        else:
            stats = (
                _scope_queryset(SaleItem.objects, pharmacy)
                .filter(medicine=medicine, sale__date__gte=start_90)
                .aggregate(total_quantity=Sum('quantity'), total_revenue=Sum('subtotal'))
            )
            qty = int(stats['total_quantity'] or 0)
            if qty < 5:
                slow_moving.append({
                    'medicine_id': int(medicine.id),
                    'medicine_name': medicine.name,
                    'medicine_sku': medicine.sku,
                    'total_quantity': int(qty),
                    'total_revenue_uzs': float(stats['total_revenue'] or 0),
                })
    slow_moving = slow_moving[:5]

    # Medicines / Inventory counts
    medicines_count = _scope_queryset(Medicine.objects, pharmacy).count()
    expiring_soon_count = _scope_queryset(Medicine.objects, pharmacy).filter(
        expiry_date__isnull=False,
        expiry_date__lte=timezone.now().date() + timedelta(days=30),
        expiry_date__gte=timezone.now().date(),
    ).count()
    low_stock_count = _scope_queryset(Inventory.objects, pharmacy).filter(current_stock__lt=F('min_stock_level')).count()

    # Recent sales (last 5)
    recent_sales = []
    recent_sales_qs = _scope_queryset(Sale.objects, pharmacy).order_by('-date')[:5]
    for sale in recent_sales_qs:
        recent_sales.append({
            'id': int(sale.id),
            'date': sale.date.isoformat(),
            'total_amount_uzs': float(sale.total_amount),
        })

    # Alerts (top 5 pending reorder recommendations)
    alerts = []
    alerts_qs = (
        _scope_queryset(ReorderRecommendation.objects, pharmacy)
        .filter(status='PENDING')
        .select_related('medicine')
        .order_by('-created_at')[:5]
    )
    for rec in alerts_qs:
        alerts.append({
            'medicine_name': rec.medicine.name,
            'recommended_quantity': int(rec.recommended_quantity),
            'priority': rec.priority,
        })

    context = {
        # Summary
        'total_sales': total_sales,
        'total_revenue_uzs': total_revenue,
        'sales_growth_pct': sales_growth_pct,
        'revenue_growth_pct': revenue_growth_pct,

        # Charts (JSON-safe lists)
        'trend_labels_json': json.dumps(trend_labels),
        'trend_sales_json': json.dumps(trend_sales),
        'trend_revenue_json': json.dumps(trend_revenue),
        'category_labels_json': json.dumps(category_labels),
        'category_revenue_json': json.dumps(category_revenue),
        'fast_moving_json': json.dumps(fast_moving),
        'slow_moving_json': json.dumps(slow_moving),
        'recent_sales_json': json.dumps(recent_sales),
        'alerts_json': json.dumps(alerts),

        # Lists
        'fast_moving_medicines': fast_moving,
        'slow_moving_medicines': slow_moving,

        # Counts
        'medicines_count': medicines_count,
        'expiring_soon_count': expiring_soon_count,
        'low_stock_count': low_stock_count,
    }
    return render(request, 'dashboard/index.html', context)
