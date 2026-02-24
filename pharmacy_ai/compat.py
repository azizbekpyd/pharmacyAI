import sys
from copy import copy as shallow_copy

import django


def patch_django42_basecontext_copy_for_py314():
    """
    Work around Django 4.2 template context copy bug on Python 3.14.
    """
    if django.VERSION[:2] != (4, 2):
        return
    if sys.version_info < (3, 14):
        return

    from django.template.context import BaseContext

    def _safe_copy(self):
        duplicate = BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = shallow_copy(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = _safe_copy

