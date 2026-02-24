from django.core.exceptions import PermissionDenied

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

