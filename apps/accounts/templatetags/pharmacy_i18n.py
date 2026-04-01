from urllib.parse import urlsplit, urlunsplit

from django import template
from django.conf import settings


register = template.Library()


def build_language_switch_path(request_or_path) -> str:
    """
    Return the current URL without any leading language prefix.

    Django's set_language view can translate canonical paths like /dashboard/
    into /ru/dashboard/ or /en/dashboard/, but it will keep an already-prefixed
    path unchanged. Stripping the current language prefix lets the switcher work
    correctly for all localized routes.
    """

    if hasattr(request_or_path, "get_full_path"):
        full_path = request_or_path.get_full_path()
    else:
        full_path = str(request_or_path or "/")

    if not full_path:
        return "/"

    parsed = urlsplit(full_path)
    supported_codes = {code for code, _label in settings.LANGUAGES}
    path = parsed.path or "/"
    segments = [segment for segment in path.split("/") if segment]

    if segments and segments[0] in supported_codes:
        segments = segments[1:]

    canonical_path = "/" if not segments else f"/{'/'.join(segments)}"
    if path.endswith("/") and canonical_path != "/" and not canonical_path.endswith("/"):
        canonical_path += "/"

    return urlunsplit(("", "", canonical_path, parsed.query, ""))


@register.simple_tag
def language_switch_path(request_or_path) -> str:
    return build_language_switch_path(request_or_path)
