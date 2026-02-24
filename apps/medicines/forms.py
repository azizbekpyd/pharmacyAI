"""
Forms for medicines template views.
"""
from django import forms
from .models import Medicine


class MedicineForm(forms.ModelForm):
    """Bootstrap-styled form for updating medicine records."""

    class Meta:
        model = Medicine
        fields = [
            "name",
            "category",
            "sku",
            "unit_price",
            "expiry_date",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "sku": forms.TextInput(attrs={"class": "form-control"}),
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
