"""
Inventory optimization services.

This module implements mathematically grounded inventory optimization with:
- Moving average forecasting (7-day and 30-day)
- Single exponential smoothing
- Forecast accuracy metrics (MAPE, MAE, RMSE)
- Reorder point calculation with safety stock

Formulas:
1) Reorder Point (ROP) = (Average Daily Demand * Lead Time) + Safety Stock
2) Safety Stock = Z * sigma * sqrt(Lead Time)
"""
from __future__ import annotations

from datetime import timedelta
from math import ceil, sqrt

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.sales.models import SaleItem
from .models import Inventory, ReorderRecommendation


class InventoryOptimizationService:
    """
    Academic inventory optimization service.

    All methods are pharmacy-scoped to preserve multi-tenant isolation.
    """

    DEFAULT_LOOKBACK_DAYS = 90
    DEFAULT_LEAD_TIME_DAYS = 7
    DEFAULT_SERVICE_LEVEL_Z = 1.65  # ~95% cycle service level
    DEFAULT_ALPHA = 0.3
    DEFAULT_FORECAST_DAYS = 30

    @staticmethod
    def calculate_daily_demand(medicine, pharmacy, lookback_days=DEFAULT_LOOKBACK_DAYS, end_date=None):
        """
        Build a daily demand time series for a medicine.

        Returns a dict with:
        - dates: ISO date labels
        - series: daily quantities sold (including zero-demand days)
        - average_daily_demand
        """
        if medicine is None or pharmacy is None:
            return {"dates": [], "series": [], "average_daily_demand": 0.0}
        if medicine.pharmacy_id != pharmacy.id:
            return {"dates": [], "series": [], "average_daily_demand": 0.0}
        if lookback_days <= 0:
            return {"dates": [], "series": [], "average_daily_demand": 0.0}

        final_day = end_date or timezone.now().date()
        start_day = final_day - timedelta(days=lookback_days - 1)

        rows = (
            SaleItem.objects.filter(
                pharmacy=pharmacy,
                medicine=medicine,
                sale__date__date__gte=start_day,
                sale__date__date__lte=final_day,
            )
            .annotate(day=TruncDate("sale__date"))
            .values("day")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("day")
        )
        demand_by_day = {row["day"]: float(row.get("total_quantity") or 0.0) for row in rows}

        dates = []
        series = []
        cursor = start_day
        while cursor <= final_day:
            dates.append(cursor.isoformat())
            series.append(float(demand_by_day.get(cursor, 0.0)))
            cursor += timedelta(days=1)

        average_daily_demand = (sum(series) / len(series)) if series else 0.0
        return {
            "dates": dates,
            "series": series,
            "average_daily_demand": average_daily_demand,
        }

    @staticmethod
    def _rolling_average(values, window):
        if not values:
            return 0.0
        if window <= 0:
            return 0.0
        window_values = values[-min(window, len(values)) :]
        return sum(window_values) / len(window_values)

    @staticmethod
    def _moving_average_predictions(values, window):
        if not values:
            return []
        if window <= 0:
            return values[:]

        predictions = []
        for idx, actual in enumerate(values):
            history = values[max(0, idx - window) : idx]
            if not history:
                predictions.append(float(actual))
            else:
                predictions.append(float(sum(history) / len(history)))
        return predictions

    @staticmethod
    def moving_average_forecast(
        medicine,
        pharmacy,
        forecast_days=DEFAULT_FORECAST_DAYS,
        lookback_days=DEFAULT_LOOKBACK_DAYS,
    ):
        """
        Compute moving-average demand forecast.

        Outputs:
        - 7-day moving average
        - 30-day moving average
        - average daily demand
        - forecasted daily demand and total horizon demand
        - in-sample accuracy metrics
        """
        demand_data = InventoryOptimizationService.calculate_daily_demand(
            medicine=medicine,
            pharmacy=pharmacy,
            lookback_days=lookback_days,
        )
        series = demand_data["series"]
        avg_daily = float(demand_data["average_daily_demand"])

        ma_7 = InventoryOptimizationService._rolling_average(series, 7)
        ma_30 = InventoryOptimizationService._rolling_average(series, 30)

        if len(series) >= 30:
            forecasted_daily_demand = (ma_7 + ma_30) / 2.0
        elif len(series) >= 7:
            forecasted_daily_demand = ma_7
        else:
            forecasted_daily_demand = avg_daily

        forecasted_quantity = max(0.0, forecasted_daily_demand * max(forecast_days, 0))

        predictions = InventoryOptimizationService._moving_average_predictions(series, 7)
        metrics = {
            "mape": InventoryOptimizationService.calculate_mape(series[1:], predictions[1:]) if len(series) > 1 else None,
            "mae": InventoryOptimizationService.calculate_mae(series[1:], predictions[1:]) if len(series) > 1 else None,
            "rmse": InventoryOptimizationService.calculate_rmse(series[1:], predictions[1:]) if len(series) > 1 else None,
        }

        return {
            "medicine_id": medicine.id,
            "method": "moving_average",
            "historical": demand_data,
            "daily_average_demand": avg_daily,
            "moving_average_7_day": ma_7,
            "moving_average_30_day": ma_30,
            "forecasted_daily_demand": forecasted_daily_demand,
            "forecasted_quantity": forecasted_quantity,
            "forecast_horizon_days": forecast_days,
            "accuracy": metrics,
        }

    @staticmethod
    def exponential_smoothing(
        medicine,
        pharmacy,
        forecast_days=DEFAULT_FORECAST_DAYS,
        alpha=DEFAULT_ALPHA,
        lookback_days=DEFAULT_LOOKBACK_DAYS,
    ):
        """
        Single Exponential Smoothing (SES).

        Recurrence:
        F(t+1) = alpha * A(t) + (1 - alpha) * F(t)
        """
        alpha = float(alpha)
        if alpha <= 0 or alpha >= 1:
            alpha = InventoryOptimizationService.DEFAULT_ALPHA

        demand_data = InventoryOptimizationService.calculate_daily_demand(
            medicine=medicine,
            pharmacy=pharmacy,
            lookback_days=lookback_days,
        )
        series = demand_data["series"]
        if not series:
            return {
                "medicine_id": medicine.id,
                "method": "exponential_smoothing",
                "historical": demand_data,
                "alpha": alpha,
                "forecasted_daily_demand": 0.0,
                "forecasted_quantity": 0.0,
                "forecast_horizon_days": forecast_days,
                "accuracy": {"mape": None, "mae": None, "rmse": None},
            }

        level = float(series[0])
        one_step_predictions = [level]
        for actual in series[1:]:
            one_step_predictions.append(level)
            level = alpha * float(actual) + (1.0 - alpha) * level

        forecasted_daily_demand = max(0.0, level)
        forecasted_quantity = forecasted_daily_demand * max(forecast_days, 0)

        metrics = {
            "mape": InventoryOptimizationService.calculate_mape(series[1:], one_step_predictions[1:])
            if len(series) > 1
            else None,
            "mae": InventoryOptimizationService.calculate_mae(series[1:], one_step_predictions[1:])
            if len(series) > 1
            else None,
            "rmse": InventoryOptimizationService.calculate_rmse(series[1:], one_step_predictions[1:])
            if len(series) > 1
            else None,
        }

        return {
            "medicine_id": medicine.id,
            "method": "exponential_smoothing",
            "historical": demand_data,
            "alpha": alpha,
            "forecasted_daily_demand": forecasted_daily_demand,
            "forecasted_quantity": forecasted_quantity,
            "forecast_horizon_days": forecast_days,
            "accuracy": metrics,
        }

    @staticmethod
    def calculate_mape(actual_values, predicted_values):
        """Mean Absolute Percentage Error (in %), ignoring zero actuals."""
        pairs = list(zip(actual_values or [], predicted_values or []))
        if not pairs:
            return None
        terms = []
        for actual, predicted in pairs:
            actual = float(actual)
            predicted = float(predicted)
            if actual == 0:
                continue
            terms.append(abs((actual - predicted) / actual))
        if not terms:
            return None
        return (sum(terms) / len(terms)) * 100.0

    @staticmethod
    def calculate_mae(actual_values, predicted_values):
        """Mean Absolute Error."""
        pairs = list(zip(actual_values or [], predicted_values or []))
        if not pairs:
            return None
        abs_errors = [abs(float(a) - float(p)) for a, p in pairs]
        return (sum(abs_errors) / len(abs_errors)) if abs_errors else None

    @staticmethod
    def calculate_rmse(actual_values, predicted_values):
        """Root Mean Squared Error."""
        pairs = list(zip(actual_values or [], predicted_values or []))
        if not pairs:
            return None
        sq_errors = [(float(a) - float(p)) ** 2 for a, p in pairs]
        if not sq_errors:
            return None
        return sqrt(sum(sq_errors) / len(sq_errors))

    @staticmethod
    def calculate_standard_deviation(daily_demand_values):
        """
        Population standard deviation of daily demand (sigma).
        """
        values = [float(v) for v in (daily_demand_values or [])]
        if not values:
            return 0.0
        mean_val = sum(values) / len(values)
        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
        return sqrt(variance)

    @staticmethod
    def calculate_safety_stock(daily_demand_values, lead_time_days=DEFAULT_LEAD_TIME_DAYS, service_level_z=DEFAULT_SERVICE_LEVEL_Z):
        """
        Safety Stock = Z * sigma * sqrt(Lead Time)
        """
        lead_time_days = max(int(lead_time_days or 0), 0)
        sigma = InventoryOptimizationService.calculate_standard_deviation(daily_demand_values)
        return float(service_level_z) * sigma * sqrt(lead_time_days) if lead_time_days > 0 else 0.0

    @staticmethod
    def compare_forecasts(
        medicine,
        pharmacy,
        forecast_days=DEFAULT_FORECAST_DAYS,
        alpha=DEFAULT_ALPHA,
        lookback_days=DEFAULT_LOOKBACK_DAYS,
    ):
        """
        Compare moving-average and exponential-smoothing forecasts by MAPE.
        """
        moving = InventoryOptimizationService.moving_average_forecast(
            medicine=medicine,
            pharmacy=pharmacy,
            forecast_days=forecast_days,
            lookback_days=lookback_days,
        )
        exponential = InventoryOptimizationService.exponential_smoothing(
            medicine=medicine,
            pharmacy=pharmacy,
            forecast_days=forecast_days,
            alpha=alpha,
            lookback_days=lookback_days,
        )

        ma_mape = moving["accuracy"].get("mape")
        es_mape = exponential["accuracy"].get("mape")

        if ma_mape is None and es_mape is None:
            selected_method = "exponential_smoothing"
            selected = exponential
        elif ma_mape is None:
            selected_method = "exponential_smoothing"
            selected = exponential
        elif es_mape is None:
            selected_method = "moving_average"
            selected = moving
        elif ma_mape <= es_mape:
            selected_method = "moving_average"
            selected = moving
        else:
            selected_method = "exponential_smoothing"
            selected = exponential

        return {
            "medicine_id": medicine.id,
            "medicine_name": medicine.name,
            "medicine_sku": medicine.sku,
            "methods": {
                "moving_average": moving,
                "exponential_smoothing": exponential,
            },
            "selected_method": selected_method,
            "selected_forecast": selected,
        }

    @staticmethod
    def calculate_reorder_point(
        medicine,
        pharmacy,
        lead_time_days=DEFAULT_LEAD_TIME_DAYS,
        service_level_z=DEFAULT_SERVICE_LEVEL_Z,
        alpha=DEFAULT_ALPHA,
        forecast_days=DEFAULT_FORECAST_DAYS,
        lookback_days=DEFAULT_LOOKBACK_DAYS,
    ):
        """
        Calculate reorder point using:
        ROP = (Average Daily Demand * Lead Time) + Safety Stock

        Safety Stock = Z * sigma * sqrt(Lead Time)
        """
        comparison = InventoryOptimizationService.compare_forecasts(
            medicine=medicine,
            pharmacy=pharmacy,
            forecast_days=forecast_days,
            alpha=alpha,
            lookback_days=lookback_days,
        )
        selected = comparison["selected_forecast"]
        daily_demand_values = selected["historical"]["series"]

        avg_daily_demand = float(selected.get("forecasted_daily_demand") or 0.0)
        lead_time_days = max(int(lead_time_days or 0), 0)
        safety_stock = InventoryOptimizationService.calculate_safety_stock(
            daily_demand_values=daily_demand_values,
            lead_time_days=lead_time_days,
            service_level_z=service_level_z,
        )
        sigma = InventoryOptimizationService.calculate_standard_deviation(daily_demand_values)
        reorder_point = (avg_daily_demand * lead_time_days) + safety_stock

        return {
            "medicine_id": medicine.id,
            "selected_method": comparison["selected_method"],
            "forecast_comparison": comparison,
            "average_daily_demand": avg_daily_demand,
            "lead_time_days": lead_time_days,
            "service_level_z": float(service_level_z),
            "standard_deviation": sigma,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
        }

    @staticmethod
    def _recommendation_priority(current_stock, reorder_point):
        if reorder_point <= 0:
            return "LOW"
        coverage_ratio = current_stock / reorder_point
        if coverage_ratio <= 0.25:
            return "URGENT"
        if coverage_ratio <= 0.5:
            return "HIGH"
        if coverage_ratio <= 0.9:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _build_reorder_quantity(inventory, reorder_point, forecasted_daily_demand, lead_time_days, safety_stock):
        """
        Determine practical reorder quantity.

        Target stock combines max stock policy and forecast coverage buffer.
        """
        projected_target_stock = int(
            ceil((forecasted_daily_demand * (lead_time_days + 30)) + safety_stock)
        )
        target_stock = max(int(inventory.max_stock_level), projected_target_stock)
        gap = target_stock - int(inventory.current_stock)
        return max(1, gap)

    @staticmethod
    def generate_reorder_recommendations(
        pharmacy,
        lead_time_days=DEFAULT_LEAD_TIME_DAYS,
        service_level_z=DEFAULT_SERVICE_LEVEL_Z,
        alpha=DEFAULT_ALPHA,
        forecast_days=DEFAULT_FORECAST_DAYS,
        lookback_days=DEFAULT_LOOKBACK_DAYS,
    ):
        """
        Persist pending reorder recommendations using academic ROP logic.

        Creates recommendations only when:
        - current_stock <= computed reorder_point
        - no existing pending recommendation exists for the medicine
        """
        if pharmacy is None:
            return []

        inventories = (
            Inventory.objects.filter(pharmacy=pharmacy)
            .select_related("medicine")
            .order_by("medicine__name")
        )
        existing_pending = set(
            ReorderRecommendation.objects.filter(pharmacy=pharmacy, status="PENDING").values_list("medicine_id", flat=True)
        )

        recommendations = []
        for inventory in inventories:
            medicine = inventory.medicine
            if medicine.id in existing_pending:
                continue

            rop_data = InventoryOptimizationService.calculate_reorder_point(
                medicine=medicine,
                pharmacy=pharmacy,
                lead_time_days=lead_time_days,
                service_level_z=service_level_z,
                alpha=alpha,
                forecast_days=forecast_days,
                lookback_days=lookback_days,
            )
            reorder_point = float(rop_data["reorder_point"])
            if float(inventory.current_stock) > reorder_point:
                continue

            selected_forecast = rop_data["forecast_comparison"]["selected_forecast"]
            forecasted_daily = float(selected_forecast.get("forecasted_daily_demand") or 0.0)
            recommended_quantity = InventoryOptimizationService._build_reorder_quantity(
                inventory=inventory,
                reorder_point=reorder_point,
                forecasted_daily_demand=forecasted_daily,
                lead_time_days=lead_time_days,
                safety_stock=float(rop_data["safety_stock"]),
            )
            priority = InventoryOptimizationService._recommendation_priority(
                current_stock=float(inventory.current_stock),
                reorder_point=reorder_point,
            )
            mape = selected_forecast["accuracy"].get("mape")
            reason = (
                f"ROP={reorder_point:.2f} (avg_demand={rop_data['average_daily_demand']:.2f} * lead_time={lead_time_days} "
                f"+ safety_stock={rop_data['safety_stock']:.2f}); "
                f"current_stock={inventory.current_stock}. "
                f"Model={rop_data['selected_method']} (MAPE={mape:.2f}%)." if mape is not None else
                f"ROP={reorder_point:.2f} (avg_demand={rop_data['average_daily_demand']:.2f} * lead_time={lead_time_days} "
                f"+ safety_stock={rop_data['safety_stock']:.2f}); "
                f"current_stock={inventory.current_stock}. Model={rop_data['selected_method']}."
            )

            recommendation = ReorderRecommendation.objects.create(
                medicine=medicine,
                pharmacy=pharmacy,
                recommended_quantity=recommended_quantity,
                reason=reason,
                priority=priority,
                status="PENDING",
            )
            recommendations.append(recommendation)

        return recommendations

    @staticmethod
    def build_dashboard_forecast_data(
        pharmacy,
        limit=10,
        lead_time_days=DEFAULT_LEAD_TIME_DAYS,
        service_level_z=DEFAULT_SERVICE_LEVEL_Z,
        alpha=DEFAULT_ALPHA,
        forecast_days=DEFAULT_FORECAST_DAYS,
        lookback_days=DEFAULT_LOOKBACK_DAYS,
    ):
        """
        Build structured inventory-optimization payload for dashboard charts.
        """
        if pharmacy is None:
            return {
                "items": [],
                "chart": {"labels": [], "forecasted_demand": [], "recommended_reorder_quantity": [], "mape": []},
                "service_level": {
                    "target_percent": 95,
                    "z_value": float(service_level_z),
                    "estimated_fill_rate_percent": None,
                },
            }

        inventories = (
            Inventory.objects.filter(pharmacy=pharmacy)
            .select_related("medicine")
            .order_by("medicine__name")[: max(int(limit or 0), 0)]
        )
        items = []
        for inventory in inventories:
            medicine = inventory.medicine
            rop_data = InventoryOptimizationService.calculate_reorder_point(
                medicine=medicine,
                pharmacy=pharmacy,
                lead_time_days=lead_time_days,
                service_level_z=service_level_z,
                alpha=alpha,
                forecast_days=forecast_days,
                lookback_days=lookback_days,
            )
            selected = rop_data["forecast_comparison"]["selected_forecast"]
            forecast_daily = float(selected.get("forecasted_daily_demand") or 0.0)
            forecast_total = float(selected.get("forecasted_quantity") or 0.0)
            reorder_point = float(rop_data["reorder_point"])
            recommended_quantity = (
                InventoryOptimizationService._build_reorder_quantity(
                    inventory=inventory,
                    reorder_point=reorder_point,
                    forecasted_daily_demand=forecast_daily,
                    lead_time_days=lead_time_days,
                    safety_stock=float(rop_data["safety_stock"]),
                )
                if float(inventory.current_stock) <= reorder_point
                else 0
            )

            item = {
                "medicine_id": medicine.id,
                "medicine_name": medicine.name,
                "medicine_sku": medicine.sku,
                "current_stock": int(inventory.current_stock),
                "reorder_point": reorder_point,
                "safety_stock": float(rop_data["safety_stock"]),
                "service_level_z": float(service_level_z),
                "service_level_percent": 95,
                "selected_method": rop_data["selected_method"],
                "forecasted_daily_demand": forecast_daily,
                "forecasted_demand_30_days": forecast_total,
                "recommended_reorder_quantity": int(recommended_quantity),
                "mape": selected["accuracy"].get("mape"),
                "mae": selected["accuracy"].get("mae"),
                "rmse": selected["accuracy"].get("rmse"),
            }
            items.append(item)

        labels = [row["medicine_name"] for row in items]
        forecast_series = [row["forecasted_demand_30_days"] for row in items]
        reorder_series = [row["recommended_reorder_quantity"] for row in items]
        mape_series = [row["mape"] if row["mape"] is not None else 0.0 for row in items]

        service_compliant = 0
        for row in items:
            if row["current_stock"] >= row["reorder_point"]:
                service_compliant += 1
        fill_rate = (service_compliant / len(items) * 100.0) if items else None

        return {
            "items": items,
            "chart": {
                "labels": labels,
                "forecasted_demand": forecast_series,
                "recommended_reorder_quantity": reorder_series,
                "mape": mape_series,
            },
            "service_level": {
                "target_percent": 95,
                "z_value": float(service_level_z),
                "estimated_fill_rate_percent": fill_rate,
            },
        }


class InventoryService:
    """
    Backward-compatible service facade.
    """

    @staticmethod
    def generate_reorder_recommendations(pharmacy):
        return InventoryOptimizationService.generate_reorder_recommendations(pharmacy=pharmacy)
