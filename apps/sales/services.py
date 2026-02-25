"""
Sales analytics and forecasting services.
"""
from datetime import timedelta

from django.db.models import Avg, Count, Max, Min, Q, Sum
from django.utils import timezone

from apps.inventory.services import InventoryOptimizationService
from apps.medicines.models import Medicine
from .models import Sale, SaleItem


class SalesAnalyticsService:
    @staticmethod
    def _scope_sales(pharmacy=None):
        queryset = Sale.objects.all()
        if pharmacy is not None:
            queryset = queryset.filter(pharmacy=pharmacy)
        return queryset

    @staticmethod
    def _scope_sale_items(pharmacy=None):
        queryset = SaleItem.objects.all()
        if pharmacy is not None:
            queryset = queryset.filter(pharmacy=pharmacy)
        return queryset

    @staticmethod
    def _scope_medicines(pharmacy=None):
        queryset = Medicine.objects.all()
        if pharmacy is not None:
            queryset = queryset.filter(pharmacy=pharmacy)
        return queryset

    @staticmethod
    def get_analytics(start_date=None, end_date=None, pharmacy=None):
        date_filter = Q()
        if start_date:
            date_filter &= Q(date__gte=start_date)
        if end_date:
            date_filter &= Q(date__lte=end_date)
        if not start_date and not end_date:
            start_date = timezone.now() - timedelta(days=30)
            date_filter = Q(date__gte=start_date)

        sales = SalesAnalyticsService._scope_sales(pharmacy).filter(date_filter)
        total_sales = sales.count()
        total_amount = sales.aggregate(Sum("total_amount"))["total_amount__sum"] or 0
        avg_sale_amount = sales.aggregate(Avg("total_amount"))["total_amount__avg"] or 0

        fast_moving = SalesAnalyticsService.get_fast_moving_medicines(days=30, limit=10, pharmacy=pharmacy)
        slow_moving = SalesAnalyticsService.get_slow_moving_medicines(days=90, pharmacy=pharmacy)
        trends = SalesAnalyticsService.get_daily_trends(days=7, pharmacy=pharmacy)
        category_analytics = SalesAnalyticsService.get_category_analytics(start_date, end_date, pharmacy=pharmacy)
        monthly_trends = SalesAnalyticsService.get_monthly_trends(start_date, end_date, pharmacy=pharmacy)
        peak_hours = SalesAnalyticsService.get_peak_hours(start_date, end_date, pharmacy=pharmacy)

        previous_period_start = None
        previous_period_end = None
        if start_date:
            period_days = (end_date - start_date).days if end_date else 30
            previous_period_end = start_date
            previous_period_start = previous_period_end - timedelta(days=period_days)

        growth_metrics = SalesAnalyticsService.get_growth_metrics(
            current_start=start_date,
            current_end=end_date,
            previous_start=previous_period_start,
            previous_end=previous_period_end,
            pharmacy=pharmacy,
        )
        forecast_accuracy = SalesAnalyticsService.get_forecast_accuracy_comparison(
            pharmacy=pharmacy,
            days=30,
            limit=10,
        )

        return {
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "summary": {
                "total_sales": total_sales,
                "total_amount": float(total_amount),
                "average_sale_amount": float(avg_sale_amount),
                "max_sale_amount": float(sales.aggregate(Max("total_amount"))["total_amount__max"] or 0),
                "min_sale_amount": float(sales.aggregate(Min("total_amount"))["total_amount__min"] or 0),
            },
            "fast_moving_medicines": fast_moving,
            "slow_moving_medicines": slow_moving,
            "trends": {
                "daily": trends,
                "monthly": monthly_trends,
            },
            "category_analytics": category_analytics,
            "peak_hours": peak_hours,
            "growth_metrics": growth_metrics,
            "forecast_accuracy": forecast_accuracy,
        }

    @staticmethod
    def get_fast_moving_medicines(days=30, limit=10, pharmacy=None):
        start_date = timezone.now() - timedelta(days=days)
        fast_moving = (
            SalesAnalyticsService._scope_sale_items(pharmacy)
            .filter(sale__date__gte=start_date)
            .values("medicine__id", "medicine__name", "medicine__sku")
            .annotate(total_quantity=Sum("quantity"), total_revenue=Sum("subtotal"), sale_count=Count("sale", distinct=True))
            .order_by("-total_quantity")[:limit]
        )
        return list(fast_moving)

    @staticmethod
    def get_slow_moving_medicines(days=90, pharmacy=None):
        start_date = timezone.now() - timedelta(days=days)
        all_medicines = SalesAnalyticsService._scope_medicines(pharmacy)
        medicines_with_sales = (
            SalesAnalyticsService._scope_sale_items(pharmacy)
            .filter(sale__date__gte=start_date)
            .values_list("medicine_id", flat=True)
            .distinct()
        )

        slow_moving = []
        for medicine in all_medicines:
            if medicine.id not in medicines_with_sales:
                slow_moving.append(
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
                SalesAnalyticsService._scope_sale_items(pharmacy)
                .filter(medicine=medicine, sale__date__gte=start_date)
                .aggregate(total_quantity=Sum("quantity"), total_revenue=Sum("subtotal"), sale_count=Count("sale", distinct=True))
            )
            if (sales_data["total_quantity"] or 0) < 5:
                slow_moving.append(
                    {
                        "medicine_id": medicine.id,
                        "medicine_name": medicine.name,
                        "medicine_sku": medicine.sku,
                        "total_quantity": sales_data["total_quantity"] or 0,
                        "total_revenue": float(sales_data["total_revenue"] or 0),
                        "sale_count": sales_data["sale_count"] or 0,
                    }
                )

        return slow_moving

    @staticmethod
    def get_daily_trends(days=7, pharmacy=None):
        start_date = timezone.now() - timedelta(days=days)
        daily_sales = (
            SalesAnalyticsService._scope_sales(pharmacy)
            .filter(date__gte=start_date)
            .extra(select={"day": "date(date)"})
            .values("day")
            .annotate(total_sales=Count("id"), total_amount=Sum("total_amount"))
            .order_by("day")
        )
        return list(daily_sales)

    @staticmethod
    def get_monthly_trends(start_date=None, end_date=None, pharmacy=None):
        date_filter = Q()
        if start_date:
            date_filter &= Q(date__gte=start_date)
        if end_date:
            date_filter &= Q(date__lte=end_date)
        if not start_date:
            start_date = timezone.now() - timedelta(days=365)
            date_filter = Q(date__gte=start_date)

        monthly_sales = (
            SalesAnalyticsService._scope_sales(pharmacy)
            .filter(date_filter)
            .extra(select={"month": "strftime('%%Y-%%m', date)"})
            .values("month")
            .annotate(total_sales=Count("id"), sum_amount=Sum("total_amount"), avg_sale_amount=Avg("total_amount"))
            .order_by("month")
        )
        results = []
        for row in monthly_sales:
            results.append(
                {
                    "month": row["month"],
                    "total_sales": row["total_sales"],
                    "total_amount": row["sum_amount"],
                    "avg_sale_amount": row["avg_sale_amount"],
                }
            )
        return results

    @staticmethod
    def get_category_analytics(start_date=None, end_date=None, pharmacy=None):
        date_filter = Q()
        if start_date:
            date_filter &= Q(sale__date__gte=start_date)
        if end_date:
            date_filter &= Q(sale__date__lte=end_date)
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
            date_filter = Q(sale__date__gte=start_date)

        category_analytics = (
            SalesAnalyticsService._scope_sale_items(pharmacy)
            .filter(date_filter)
            .values("medicine__category__id", "medicine__category__name")
            .annotate(
                total_quantity=Sum("quantity"),
                total_revenue=Sum("subtotal"),
                sale_count=Count("sale", distinct=True),
                medicine_count=Count("medicine", distinct=True),
            )
            .order_by("-total_revenue")
        )
        return list(category_analytics)

    @staticmethod
    def get_peak_hours(start_date=None, end_date=None, pharmacy=None):
        date_filter = Q()
        if start_date:
            date_filter &= Q(date__gte=start_date)
        if end_date:
            date_filter &= Q(date__lte=end_date)
        if not start_date:
            start_date = timezone.now() - timedelta(days=30)
            date_filter = Q(date__gte=start_date)

        hourly_sales = (
            SalesAnalyticsService._scope_sales(pharmacy)
            .filter(date_filter)
            .extra(select={"hour": "strftime('%%H', date)"})
            .values("hour")
            .annotate(total_sales=Count("id"), total_amount=Sum("total_amount"))
            .order_by("hour")
        )
        return list(hourly_sales)

    @staticmethod
    def get_growth_metrics(current_start=None, current_end=None, previous_start=None, previous_end=None, pharmacy=None):
        if not previous_start or not previous_end:
            return {
                "sales_growth": None,
                "revenue_growth": None,
                "message": "Previous period data not available for comparison",
            }

        current_sales = SalesAnalyticsService._scope_sales(pharmacy).filter(
            date__gte=current_start if current_start else timezone.now() - timedelta(days=30),
            date__lte=current_end if current_end else timezone.now(),
        )
        current_count = current_sales.count()
        current_revenue = current_sales.aggregate(Sum("total_amount"))["total_amount__sum"] or 0

        previous_sales = SalesAnalyticsService._scope_sales(pharmacy).filter(date__gte=previous_start, date__lte=previous_end)
        previous_count = previous_sales.count()
        previous_revenue = previous_sales.aggregate(Sum("total_amount"))["total_amount__sum"] or 0

        sales_growth = None
        revenue_growth = None
        if previous_count > 0:
            sales_growth = ((current_count - previous_count) / previous_count) * 100
        if previous_revenue > 0:
            revenue_growth = ((float(current_revenue) - float(previous_revenue)) / float(previous_revenue)) * 100

        return {
            "current_period": {"sales_count": current_count, "revenue": float(current_revenue)},
            "previous_period": {"sales_count": previous_count, "revenue": float(previous_revenue)},
            "sales_growth": round(sales_growth, 2) if sales_growth is not None else None,
            "revenue_growth": round(revenue_growth, 2) if revenue_growth is not None else None,
        }

    @staticmethod
    def get_medicine_performance(medicine_id, days=30, pharmacy=None):
        start_date = timezone.now() - timedelta(days=days)
        try:
            medicine = SalesAnalyticsService._scope_medicines(pharmacy).get(id=medicine_id)
        except Medicine.DoesNotExist:
            return None

        sale_items = SalesAnalyticsService._scope_sale_items(pharmacy).filter(medicine=medicine, sale__date__gte=start_date)
        total_quantity = sale_items.aggregate(Sum("quantity"))["quantity__sum"] or 0
        total_revenue = sale_items.aggregate(Sum("subtotal"))["subtotal__sum"] or 0
        sale_count = sale_items.values("sale").distinct().count()

        avg_quantity_per_sale = total_quantity / sale_count if sale_count > 0 else 0
        avg_revenue_per_sale = float(total_revenue) / sale_count if sale_count > 0 else 0
        avg_daily_quantity = total_quantity / days if days > 0 else 0
        avg_daily_revenue = float(total_revenue) / days if days > 0 else 0

        return {
            "medicine_id": medicine.id,
            "medicine_name": medicine.name,
            "medicine_sku": medicine.sku,
            "period_days": days,
            "metrics": {
                "total_quantity_sold": total_quantity,
                "total_revenue": float(total_revenue),
                "sale_count": sale_count,
                "avg_quantity_per_sale": round(avg_quantity_per_sale, 2),
                "avg_revenue_per_sale": round(avg_revenue_per_sale, 2),
                "avg_daily_quantity": round(avg_daily_quantity, 2),
                "avg_daily_revenue": round(avg_daily_revenue, 2),
            },
        }

    @staticmethod
    def get_forecast_accuracy_comparison(pharmacy=None, days=30, limit=10, alpha=0.3):
        """
        Compare forecast models (moving average vs exponential smoothing) for top medicines.
        """
        start_date = timezone.now() - timedelta(days=days)
        medicine_ids = list(
            SalesAnalyticsService._scope_sale_items(pharmacy)
            .filter(sale__date__gte=start_date)
            .values("medicine_id")
            .annotate(total_qty=Sum("quantity"))
            .order_by("-total_qty")
            .values_list("medicine_id", flat=True)[:limit]
        )
        if not medicine_ids:
            medicine_ids = list(
                SalesAnalyticsService._scope_medicines(pharmacy).order_by("name").values_list("id", flat=True)[:limit]
            )

        medicines = SalesAnalyticsService._scope_medicines(pharmacy).filter(id__in=medicine_ids)
        results = []
        for medicine in medicines:
            comparison = InventoryOptimizationService.compare_forecasts(
                medicine=medicine,
                pharmacy=medicine.pharmacy if pharmacy is None else pharmacy,
                forecast_days=days,
                alpha=alpha,
            )
            selected = comparison["selected_forecast"]
            results.append(
                {
                    "medicine_id": medicine.id,
                    "medicine_name": medicine.name,
                    "medicine_sku": medicine.sku,
                    "selected_method": comparison["selected_method"],
                    "mape": selected["accuracy"].get("mape"),
                    "mae": selected["accuracy"].get("mae"),
                    "rmse": selected["accuracy"].get("rmse"),
                    "forecasted_daily_demand": selected.get("forecasted_daily_demand"),
                    "forecasted_quantity": selected.get("forecasted_quantity"),
                }
            )

        avg_mape_values = [row["mape"] for row in results if row["mape"] is not None]
        avg_mape = (sum(avg_mape_values) / len(avg_mape_values)) if avg_mape_values else None
        return {"count": len(results), "average_mape": avg_mape, "results": results}


class DemandForecastingService:
    """
    Forecasting facade backed by InventoryOptimizationService.
    """

    METHOD_ALIASES = {
        "sma": "moving_average",
        "moving_average": "moving_average",
        "weighted": "moving_average",
        "trend": "moving_average",
        "exponential": "exponential_smoothing",
        "exponential_smoothing": "exponential_smoothing",
    }

    @staticmethod
    def _normalize_method(method):
        return DemandForecastingService.METHOD_ALIASES.get((method or "").lower(), "moving_average")

    @staticmethod
    def _format_result(medicine, method, result):
        historical = result.get("historical", {})
        return {
            "medicine_id": medicine.id,
            "medicine_name": medicine.name,
            "medicine_sku": medicine.sku,
            "method": method,
            "historical_data": {
                "lookback_days": len(historical.get("series", [])),
                "average_daily_sales": round(float(result.get("daily_average_demand") or 0.0), 4),
                "moving_average_7_day": round(float(result.get("moving_average_7_day") or 0.0), 4)
                if method == "moving_average"
                else None,
                "moving_average_30_day": round(float(result.get("moving_average_30_day") or 0.0), 4)
                if method == "moving_average"
                else None,
                "smoothing_factor": result.get("alpha") if method == "exponential_smoothing" else None,
            },
            "forecast": {
                "forecast_days": result.get("forecast_horizon_days"),
                "forecasted_daily_demand": round(float(result.get("forecasted_daily_demand") or 0.0), 4),
                "forecasted_quantity": round(float(result.get("forecasted_quantity") or 0.0), 4),
            },
            "accuracy": {
                "mape": result.get("accuracy", {}).get("mape"),
                "mae": result.get("accuracy", {}).get("mae"),
                "rmse": result.get("accuracy", {}).get("rmse"),
            },
        }

    @staticmethod
    def get_forecast(days=30, medicine_id=None, method="sma", pharmacy=None, alpha=0.3):
        normalized = DemandForecastingService._normalize_method(method)
        medicines = (
            SalesAnalyticsService._scope_medicines(pharmacy).filter(id=medicine_id)
            if medicine_id
            else SalesAnalyticsService._scope_medicines(pharmacy)
        )

        forecasts = []
        forecasts_by_medicine = {}
        for medicine in medicines:
            scoped_pharmacy = medicine.pharmacy if pharmacy is None else pharmacy
            if normalized == "exponential_smoothing":
                raw = InventoryOptimizationService.exponential_smoothing(
                    medicine=medicine,
                    pharmacy=scoped_pharmacy,
                    forecast_days=days,
                    alpha=alpha,
                )
            else:
                raw = InventoryOptimizationService.moving_average_forecast(
                    medicine=medicine,
                    pharmacy=scoped_pharmacy,
                    forecast_days=days,
                )

            formatted = DemandForecastingService._format_result(
                medicine=medicine,
                method=normalized,
                result=raw,
            )
            forecasts.append(formatted)
            forecasts_by_medicine[str(medicine.id)] = formatted

        return {
            "forecast_period_days": days,
            "method": normalized,
            "forecasts": forecasts,
            "forecasts_by_medicine": forecasts_by_medicine,
        }

    @staticmethod
    def get_forecast_comparison(medicine_id, days=30, pharmacy=None, alpha=0.3):
        try:
            medicine = SalesAnalyticsService._scope_medicines(pharmacy).get(id=medicine_id)
        except Medicine.DoesNotExist:
            return None

        scoped_pharmacy = medicine.pharmacy if pharmacy is None else pharmacy
        comparison = InventoryOptimizationService.compare_forecasts(
            medicine=medicine,
            pharmacy=scoped_pharmacy,
            forecast_days=days,
            alpha=alpha,
        )

        moving = DemandForecastingService._format_result(
            medicine=medicine,
            method="moving_average",
            result=comparison["methods"]["moving_average"],
        )
        exponential = DemandForecastingService._format_result(
            medicine=medicine,
            method="exponential_smoothing",
            result=comparison["methods"]["exponential_smoothing"],
        )

        return {
            "medicine_id": medicine.id,
            "forecast_days": days,
            "selected_method": comparison["selected_method"],
            "methods": {
                "moving_average": moving,
                "exponential_smoothing": exponential,
            },
        }
