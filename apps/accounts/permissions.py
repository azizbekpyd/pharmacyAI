from rest_framework.permissions import BasePermission, SAFE_METHODS


def _is_superuser(user):
    return bool(getattr(user, "is_superuser", False))


def _is_admin(user):
    return _is_superuser(user) or bool(getattr(user, "is_admin", lambda: False)())


def _is_manager(user):
    return bool(getattr(user, "is_manager", lambda: False)())


def _is_pharmacist(user):
    return bool(getattr(user, "is_pharmacist", lambda: False)())


def can_manage_medicines(user):
    return _is_admin(user) or _is_manager(user)


def can_delete_medicines(user):
    return _is_admin(user)


def can_create_sales(user):
    return _is_admin(user) or _is_manager(user) or _is_pharmacist(user)


def can_manage_sales(user):
    return _is_admin(user) or _is_manager(user)


def can_manage_inventory(user):
    return _is_admin(user) or _is_manager(user)


class CategoryRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return can_manage_medicines(user)


class MedicineRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True

        if getattr(view, "action", None) == "destroy":
            return can_delete_medicines(user)
        return can_manage_medicines(user)


class SaleRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True

        action = getattr(view, "action", None)
        if action == "create":
            return can_create_sales(user)
        return can_manage_sales(user)


class InventoryRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return can_manage_inventory(user)


class ReorderRecommendationRolePermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return can_manage_inventory(user)
