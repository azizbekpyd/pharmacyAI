from django.conf import settings
from django.contrib import messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect

from .models import Pharmacy
from .services import SubscriptionService
from .utils import require_user_pharmacy


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.pharmacy = None

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            if user.is_superuser:
                request.pharmacy = None
            else:
                pharmacy = require_user_pharmacy(user)
                if pharmacy is None:
                    raise PermissionDenied("User is not assigned to a pharmacy.")
                request.pharmacy = pharmacy

        response = self.get_response(request)
        return response


class DemoModeMiddleware:
    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.demo_mode = False
        request.demo_write_blocked = False
        request.demo_pharmacy = None

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            request.session.pop("demo_mode", None)
            return self.get_response(request)

        demo_query = (request.GET.get("demo") or "").strip().lower()
        if demo_query in {"true", "1", "yes", "on"}:
            request.session["demo_mode"] = True
        elif demo_query in {"false", "0", "no", "off"}:
            request.session["demo_mode"] = False

        request.demo_mode = bool(request.session.get("demo_mode"))
        request.demo_write_blocked = request.demo_mode and request.method in self.UNSAFE_METHODS

        if request.demo_mode and not user.is_superuser:
            demo_name = getattr(settings, "DEMO_PHARMACY_NAME", "Pharmacy Alpha")
            demo_pharmacy = Pharmacy.objects.filter(name=demo_name).first()
            if demo_pharmacy is not None:
                request.demo_pharmacy = demo_pharmacy
                request.pharmacy = demo_pharmacy
                user.pharmacy = demo_pharmacy

        return self.get_response(request)


class SubscriptionAccessMiddleware:
    UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def _is_api_request(self, request):
        accept_header = request.headers.get("Accept", "") or ""
        content_type = request.content_type or ""
        return (
            request.path.startswith("/api/")
            or "application/json" in accept_header
            or content_type.startswith("application/json")
        )

    def _blocked_response(self, request, message):
        if self._is_api_request(request):
            return JsonResponse({"detail": message}, status=403)
        if not hasattr(request, "_messages"):
            request._messages = FallbackStorage(request)
        messages.warning(request, message)
        return redirect(request.META.get("HTTP_REFERER") or "/dashboard/")

    def __call__(self, request):
        request.subscription_expired = False
        request.subscription_days_remaining = None

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        if getattr(request, "demo_mode", False) and request.method in self.UNSAFE_METHODS:
            return self._blocked_response(request, "Demo mode is read-only.")

        if user.is_superuser:
            return self.get_response(request)

        pharmacy = getattr(request, "pharmacy", None) or require_user_pharmacy(user)
        is_active = SubscriptionService.is_subscription_active(pharmacy)
        request.subscription_days_remaining = SubscriptionService.days_remaining(pharmacy)

        if not is_active:
            request.subscription_expired = True
            if request.method in self.UNSAFE_METHODS:
                return self._blocked_response(
                    request,
                    "Subscription expired. Your account is currently in read-only mode.",
                )

        return self.get_response(request)
