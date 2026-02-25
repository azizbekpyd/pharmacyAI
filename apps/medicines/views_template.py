"""
Template views for medicines app.
"""
import json
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST, require_http_methods

from apps.inventory.models import Inventory
from apps.accounts.permissions import can_delete_medicines, can_manage_medicines
from apps.tenants.models import Pharmacy
from apps.tenants.utils import require_user_pharmacy
from .models import Category, Medicine
from .services import MedicineService


class MedicineUpdateForm(forms.ModelForm):
    """Form for editing medicine data together with inventory stock."""

    stock = forms.IntegerField(
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Current stock quantity",
    )

    class Meta:
        model = Medicine
        fields = [
            "name",
            "category",
            "unit_price",
            "expiry_date",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        pharmacy = kwargs.pop("pharmacy", None)
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        if pharmacy is not None:
            self.fields["category"].queryset = self.fields["category"].queryset.filter(pharmacy=pharmacy)
        if self.instance and self.instance.pk:
            self.fields["stock"].initial = getattr(
                getattr(self.instance, "inventory", None), "current_stock", 0
            )

    def save(self, commit=True):
        medicine = super().save(commit=commit)
        stock_value = self.cleaned_data.get("stock")
        if stock_value is not None:
            inventory, _ = Inventory.objects.get_or_create(medicine=medicine, pharmacy=medicine.pharmacy)
            inventory.current_stock = stock_value
            inventory.save(update_fields=["current_stock", "updated_at"])
        return medicine


def _tenant_medicine_queryset(request):
    queryset = Medicine.objects.select_related("category", "pharmacy")
    if request.user.is_superuser:
        return queryset
    pharmacy = require_user_pharmacy(request.user)
    return queryset.filter(pharmacy=pharmacy)


@login_required
def medicine_list_view(request: HttpRequest) -> HttpResponse:
    """Render medicines list page."""
    context = {
        "can_manage_medicines": can_manage_medicines(request.user),
        "can_delete_medicines": can_delete_medicines(request.user),
    }
    return render(request, "medicines/list.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def medicine_create_view(request: HttpRequest) -> HttpResponse:
    """
    Render medicine create page and handle medicine+inventory creation.

    For JSON POST (template fetch), returns JSON response.
    """
    if request.method == "GET":
        if not can_manage_medicines(request.user):
            raise PermissionDenied("You do not have permission to create medicines.")
        return render(request, "medicines/create.html")

    if not can_manage_medicines(request.user):
        raise PermissionDenied("You do not have permission to create medicines.")

    content_type = request.content_type or ""
    is_json = content_type.startswith("application/json")
    if is_json:
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (TypeError, ValueError):
            return JsonResponse({"detail": "Invalid JSON payload."}, status=400)
    else:
        payload = request.POST

    pharmacy = None
    if request.user.is_superuser:
        pharmacy_id = payload.get("pharmacy_id") or request.GET.get("pharmacy_id")
        if pharmacy_id:
            pharmacy = Pharmacy.objects.filter(id=pharmacy_id).first()
    else:
        pharmacy = require_user_pharmacy(request.user)

    if pharmacy is None:
        error = {"pharmacy": "Pharmacy is required for medicine creation."}
        if is_json:
            return JsonResponse(error, status=400)
        messages.error(request, error["pharmacy"])
        return render(request, "medicines/create.html", status=400)

    name = (payload.get("name") or "").strip()
    sku = (payload.get("sku") or "").strip()
    description = (payload.get("description") or "").strip() or None
    expiry_date = payload.get("expiry_date") or None
    category_id = payload.get("category_id") or payload.get("category") or None
    initial_stock_raw = payload.get("initial_stock", payload.get("stock", 0))
    unit_price_raw = payload.get("unit_price")

    errors = {}
    if not name:
        errors["name"] = "Medicine name is required."
    if not sku:
        errors["sku"] = "SKU is required."
    if unit_price_raw in (None, ""):
        errors["unit_price"] = "Unit price is required."

    category = None
    if category_id:
        category = Category.objects.filter(id=category_id, pharmacy=pharmacy).first()
        if category is None:
            errors["category"] = "Selected category is invalid for this pharmacy."

    try:
        initial_stock = int(initial_stock_raw or 0)
        if initial_stock < 0:
            errors["initial_stock"] = "Initial stock must be non-negative."
    except (TypeError, ValueError):
        errors["initial_stock"] = "Initial stock must be an integer."
        initial_stock = 0

    try:
        unit_price = Decimal(str(unit_price_raw)) if unit_price_raw not in (None, "") else None
        if unit_price is not None and unit_price <= 0:
            errors["unit_price"] = "Unit price must be greater than 0."
    except (InvalidOperation, TypeError, ValueError):
        errors["unit_price"] = "Unit price is invalid."
        unit_price = None

    if expiry_date is not None:
        parsed_expiry = parse_date(str(expiry_date))
        if parsed_expiry is None:
            errors["expiry_date"] = "Expiry date is invalid."
        expiry_date = parsed_expiry

    if errors:
        if is_json:
            return JsonResponse(errors, status=400)
        for message in errors.values():
            messages.error(request, message)
        return render(request, "medicines/create.html", status=400)

    medicine_data = {
        "name": name,
        "sku": sku,
        "category": category,
        "description": description,
        "unit_price": unit_price,
        "expiry_date": expiry_date,
    }

    try:
        with transaction.atomic():
            medicine = MedicineService.create_medicine_with_inventory(
                pharmacy=pharmacy,
                medicine_data=medicine_data,
                initial_stock=initial_stock,
                enforce_limits=not request.user.is_superuser,
            )
    except ValidationError as exc:
        detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
        if is_json:
            return JsonResponse(detail, status=400)
        for value in detail.values():
            if isinstance(value, list):
                for msg in value:
                    messages.error(request, msg)
            else:
                messages.error(request, str(value))
        return render(request, "medicines/create.html", status=400)
    except IntegrityError:
        error = {"sku": "A medicine with this SKU already exists in this pharmacy."}
        if is_json:
            return JsonResponse(error, status=400)
        messages.error(request, error["sku"])
        return render(request, "medicines/create.html", status=400)

    if is_json:
        current_stock = medicine.inventory.current_stock if hasattr(medicine, "inventory") else 0
        return JsonResponse(
            {
                "id": medicine.id,
                "name": medicine.name,
                "sku": medicine.sku,
                "current_stock": current_stock,
            },
            status=201,
        )

    messages.success(request, "Medicine created successfully")
    return redirect("medicines-list")


@login_required
def medicine_detail_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render medicine detail page (read-only)."""
    medicine = get_object_or_404(_tenant_medicine_queryset(request), pk=pk)
    return render(request, "medicines/detail.html", {"medicine": medicine})


@login_required
@require_http_methods(["GET", "POST"])
def medicine_update_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Render and process medicine update form."""
    if not can_manage_medicines(request.user):
        raise PermissionDenied("You do not have permission to update medicines.")

    medicine = get_object_or_404(_tenant_medicine_queryset(request), pk=pk)
    pharmacy = medicine.pharmacy

    if request.method == "POST":
        form = MedicineUpdateForm(request.POST, instance=medicine, pharmacy=pharmacy)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "Medicine updated successfully")
            return redirect("medicines-list")
    else:
        form = MedicineUpdateForm(instance=medicine, pharmacy=pharmacy)

    return render(
        request,
        "medicines/edit.html",
        {
            "form": form,
            "medicine": medicine,
        },
    )


@login_required
@require_POST
def medicine_delete_view(request: HttpRequest, pk: int) -> HttpResponse:
    """Delete a medicine by POST request only."""
    if not can_delete_medicines(request.user):
        raise PermissionDenied("You do not have permission to delete medicines.")

    medicine = get_object_or_404(_tenant_medicine_queryset(request), pk=pk)

    try:
        medicine.delete()
        messages.success(request, "Medicine deleted successfully.")
    except ProtectedError:
        messages.error(
            request,
            "This medicine cannot be deleted because it is used in existing sales records.",
        )

    return redirect("medicines-list")


@login_required
def category_list_view(request: HttpRequest) -> HttpResponse:
    """Render categories list page."""
    return render(request, "medicines/categories.html")
