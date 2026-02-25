"""
Template views for sales app.
"""
import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.shortcuts import render
from django.utils import timezone

from apps.tenants.utils import require_user_pharmacy
from .models import Sale, SaleItem


def _scope_queryset(queryset, pharmacy):
    if pharmacy is None:
        return queryset
    return queryset.filter(pharmacy=pharmacy)


@login_required
def sales_list_view(request):
    """Render sales list page."""
    if request.GET.get("created") == "1":
        messages.success(request, "Sale created successfully")
    return render(request, "sales/list.html")


@login_required
def sales_analytics_view(request):
    """
    Render sales analytics page with calculated data.
    """
    pharmacy = None if request.user.is_superuser else require_user_pharmacy(request.user)

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    if start_date:
        from datetime import datetime

        try:
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except Exception:
            start_date = None
    if end_date:
        from datetime import datetime

        try:
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except Exception:
            end_date = None

    date_filter = Q()
    if start_date:
        date_filter &= Q(date__gte=start_date)
    if end_date:
        date_filter &= Q(date__lte=end_date)
    if not start_date and not end_date:
        start_date = timezone.now() - timedelta(days=30)
        date_filter = Q(date__gte=start_date)

    sales_queryset = _scope_queryset(Sale.objects.filter(date_filter), pharmacy)
    total_sales = sales_queryset.count()
    revenue_result = sales_queryset.aggregate(total=Sum("total_amount"))
    total_revenue = float(revenue_result["total"] or 0)
    average_sale = total_revenue / total_sales if total_sales > 0 else 0.0

    trend_start_date = start_date if start_date else timezone.now() - timedelta(days=30)
    trend_end_date = end_date if end_date else timezone.now()
    trend_filter = Q(date__gte=trend_start_date, date__lte=trend_end_date)
    daily_trends = (
        _scope_queryset(Sale.objects, pharmacy)
        .filter(trend_filter)
        .extra(select={"day": "date(date)"})
        .values("day")
        .annotate(total_sales=Count("id"), total_amount=Sum("total_amount"))
        .order_by("day")
    )

    sales_trend_list = []
    trend_labels = []
    trend_sales_data = []
    trend_revenue_data = []
    for item in daily_trends:
        day_str = str(item["day"])
        day_sales = item.get("total_sales", 0)
        day_revenue = float(item.get("total_amount", 0))
        sales_trend_list.append({"day": day_str, "total_sales": day_sales, "total_amount": day_revenue})
        trend_labels.append(day_str)
        trend_sales_data.append(day_sales)
        trend_revenue_data.append(day_revenue)

    category_start_date = start_date if start_date else timezone.now() - timedelta(days=30)
    category_dist = (
        _scope_queryset(SaleItem.objects, pharmacy)
        .filter(sale__date__gte=category_start_date)
        .values("medicine__category__id", "medicine__category__name")
        .annotate(total_quantity=Sum("quantity"), total_revenue=Sum("subtotal"), sale_count=Count("sale", distinct=True))
        .order_by("-total_revenue")
    )

    category_list = []
    category_labels = []
    category_revenue_data = []
    for item in category_dist:
        cat_name = item.get("medicine__category__name") or "Uncategorized"
        cat_revenue = float(item.get("total_revenue", 0))
        cat_quantity = item.get("total_quantity", 0)
        category_list.append(
            {
                "medicine__category__name": cat_name,
                "total_revenue": cat_revenue,
                "total_quantity": cat_quantity,
            }
        )
        category_labels.append(cat_name)
        category_revenue_data.append(cat_revenue)

    fast_start_date = timezone.now() - timedelta(days=30)
    fast_moving = (
        _scope_queryset(SaleItem.objects, pharmacy)
        .filter(sale__date__gte=fast_start_date)
        .values("medicine__id", "medicine__name", "medicine__sku")
        .annotate(total_quantity=Sum("quantity"), total_revenue=Sum("subtotal"), sale_count=Count("sale", distinct=True))
        .order_by("-total_quantity")[:10]
    )

    slow_start_date = timezone.now() - timedelta(days=90)
    from apps.medicines.models import Medicine

    all_medicines = _scope_queryset(Medicine.objects, pharmacy).all()
    medicines_with_sales = (
        _scope_queryset(SaleItem.objects, pharmacy)
        .filter(sale__date__gte=slow_start_date)
        .values_list("medicine_id", flat=True)
        .distinct()
    )

    slow_moving_list = []
    for medicine in all_medicines:
        if medicine.id not in medicines_with_sales:
            slow_moving_list.append(
                {
                    "medicine_id": medicine.id,
                    "medicine_name": medicine.name,
                    "medicine_sku": medicine.sku,
                    "total_quantity": 0,
                    "total_revenue": 0,
                    "sale_count": 0,
                }
            )
            continue

        sales_data = (
            _scope_queryset(SaleItem.objects, pharmacy)
            .filter(medicine=medicine, sale__date__gte=slow_start_date)
            .aggregate(total_quantity=Sum("quantity"), total_revenue=Sum("subtotal"), sale_count=Count("sale", distinct=True))
        )
        if (sales_data["total_quantity"] or 0) < 5:
            slow_moving_list.append(
                {
                    "medicine_id": medicine.id,
                    "medicine_name": medicine.name,
                    "medicine_sku": medicine.sku,
                    "total_quantity": sales_data["total_quantity"] or 0,
                    "total_revenue": float(sales_data["total_revenue"] or 0),
                    "sale_count": sales_data["sale_count"] or 0,
                }
            )

    growth_percentage = None
    if start_date:
        period_days = (end_date - start_date).days if end_date else 30
        previous_period_end = start_date
        previous_period_start = previous_period_end - timedelta(days=period_days)
        current_revenue = total_revenue

        previous_sales = _scope_queryset(
            Sale.objects.filter(date__gte=previous_period_start, date__lt=previous_period_end),
            pharmacy,
        )
        previous_revenue_result = previous_sales.aggregate(total=Sum("total_amount"))
        previous_revenue = float(previous_revenue_result["total"] or 0)
        if previous_revenue > 0:
            growth_percentage = ((current_revenue - previous_revenue) / previous_revenue) * 100

    context = {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "average_sale": average_sale,
        "growth_percentage": growth_percentage,
        "sales_trend_labels_json": json.dumps(trend_labels),
        "sales_trend_sales_json": json.dumps(trend_sales_data),
        "sales_trend_revenue_json": json.dumps(trend_revenue_data),
        "sales_trend": sales_trend_list,
        "category_labels_json": json.dumps(category_labels),
        "category_revenue_json": json.dumps(category_revenue_data),
        "category_distribution": category_list,
        "fast_moving_medicines": [{**item, "total_revenue": float(item.get("total_revenue", 0))} for item in list(fast_moving)],
        "slow_moving_medicines": [{**item, "total_revenue": float(item.get("total_revenue", 0))} for item in slow_moving_list[:10]],
    }

    return render(request, "sales/analytics.html", context)


@login_required
def sales_forecast_view(request):
    """Render demand forecasting page."""
    return render(request, "sales/forecast.html")
