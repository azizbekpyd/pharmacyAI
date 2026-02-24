from django.core.exceptions import PermissionDenied


def get_user_pharmacy(user):
    if not getattr(user, "is_authenticated", False):
        return None
    if getattr(user, "is_superuser", False):
        return None
    return getattr(user, "pharmacy", None)


def require_user_pharmacy(user):
    pharmacy = get_user_pharmacy(user)
    if getattr(user, "is_authenticated", False) and not getattr(user, "is_superuser", False) and pharmacy is None:
        raise PermissionDenied("User is not assigned to a pharmacy.")
    return pharmacy

