"""
API views for sales app.

Handles CRUD operations for sales, plus analytics and forecasting.
"""
from datetime import datetime

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.permissions import SaleRolePermission
from apps.tenants.mixins import TenantScopedQuerysetMixin
from apps.tenants.models import Pharmacy
from apps.tenants.utils import require_user_pharmacy
from .models import Sale
from .serializers import SaleCreateSerializer, SaleListSerializer, SaleSerializer
from .services import DemandForecastingService, SalesAnalyticsService


class SaleViewSet(TenantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Sale.objects.select_related("user", "pharmacy").prefetch_related("items__medicine").all()
    permission_classes = [SaleRolePermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["notes", "user__username"]
    ordering_fields = ["date", "total_amount", "created_at"]
    ordering = ["-date"]

    def get_serializer_class(self):
        if self.action == "create":
            return SaleCreateSerializer
        if self.action == "list":
            return SaleListSerializer
        return SaleSerializer

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED and isinstance(response.data, dict):
            response.data["message"] = "Sale created successfully"
        return response

    def _resolve_action_pharmacy(self):
        user = self.request.user
        if user.is_superuser:
            pharmacy_id = self.request.query_params.get("pharmacy_id") or self.request.data.get("pharmacy")
            if pharmacy_id:
                return Pharmacy.objects.filter(id=pharmacy_id).first()
            return None
        return require_user_pharmacy(user)

    def get_queryset(self):
        queryset = self.get_tenant_queryset(super().get_queryset())

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        analytics = SalesAnalyticsService.get_analytics(start_date=start_date, end_date=end_date, pharmacy=pharmacy)
        return Response(analytics, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def forecast(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 30))
        medicine_id = request.query_params.get("medicine_id")
        method = request.query_params.get("method", "sma")
        forecast = DemandForecastingService.get_forecast(
            days=days,
            medicine_id=medicine_id,
            method=method,
            pharmacy=pharmacy,
        )
        return Response(forecast, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def forecast_comparison(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        medicine_id = request.query_params.get("medicine_id")
        days = int(request.query_params.get("days", 30))
        if not medicine_id:
            return Response({"error": "medicine_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        comparison = DemandForecastingService.get_forecast_comparison(
            medicine_id=medicine_id,
            days=days,
            pharmacy=pharmacy,
        )
        if comparison is None:
            return Response({"error": "Medicine not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(comparison, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def category_analytics(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        analytics = SalesAnalyticsService.get_category_analytics(
            start_date=start_date,
            end_date=end_date,
            pharmacy=pharmacy,
        )
        return Response(analytics, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def monthly_trends(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        trends = SalesAnalyticsService.get_monthly_trends(
            start_date=start_date,
            end_date=end_date,
            pharmacy=pharmacy,
        )
        return Response(trends, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def medicine_performance(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        medicine_id = request.query_params.get("medicine_id")
        days = int(request.query_params.get("days", 30))
        if not medicine_id:
            return Response({"error": "medicine_id parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        performance = SalesAnalyticsService.get_medicine_performance(
            medicine_id=medicine_id,
            days=days,
            pharmacy=pharmacy,
        )
        if performance is None:
            return Response({"error": "Medicine not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(performance, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def fast_moving(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 30))
        limit = int(request.query_params.get("limit", 10))
        fast_moving = SalesAnalyticsService.get_fast_moving_medicines(days=days, limit=limit, pharmacy=pharmacy)
        return Response(fast_moving, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def slow_moving(self, request):
        pharmacy = self._resolve_action_pharmacy()
        if request.user.is_superuser and request.query_params.get("pharmacy_id") and pharmacy is None:
            return Response({"error": "Pharmacy not found"}, status=status.HTTP_404_NOT_FOUND)

        days = int(request.query_params.get("days", 90))
        slow_moving = SalesAnalyticsService.get_slow_moving_medicines(days=days, pharmacy=pharmacy)
        return Response(slow_moving, status=status.HTTP_200_OK)
