from django.core.exceptions import PermissionDenied

from .utils import require_user_pharmacy


class TenantScopedQuerysetMixin:
    pharmacy_field = "pharmacy"

    def get_requested_pharmacy_for_superuser(self):
        user = self.request.user
        if not user.is_superuser:
            return None

        pharmacy_id = self.request.query_params.get("pharmacy_id")
        if pharmacy_id:
            return pharmacy_id
        return None

    def get_tenant_queryset(self, queryset):
        user = self.request.user
        if user.is_superuser:
            pharmacy_id = self.get_requested_pharmacy_for_superuser()
            if pharmacy_id:
                return queryset.filter(**{f"{self.pharmacy_field}_id": pharmacy_id})
            return queryset

        pharmacy = require_user_pharmacy(user)
        return queryset.filter(**{self.pharmacy_field: pharmacy})

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_superuser:
            pharmacy_id = self.request.data.get("pharmacy")
            if pharmacy_id:
                serializer.save(**{f"{self.pharmacy_field}_id": pharmacy_id})
            else:
                serializer.save()
            return

        pharmacy = require_user_pharmacy(user)
        serializer.save(**{self.pharmacy_field: pharmacy})

    def perform_update(self, serializer):
        user = self.request.user
        if user.is_superuser:
            serializer.save()
            return

        if self.pharmacy_field in serializer.validated_data:
            raise PermissionDenied("Changing pharmacy is not allowed.")

        pharmacy = require_user_pharmacy(user)
        serializer.save(**{self.pharmacy_field: pharmacy})

