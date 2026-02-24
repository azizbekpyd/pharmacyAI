"""
Template URL configuration for medicines app.
"""
from django.urls import path

from .views_template import (
    category_list_view,
    medicine_create_view,
    medicine_delete_view,
    medicine_detail_view,
    medicine_list_view,
    medicine_update_view,
)

# No app_name to avoid namespace conflicts with API URLs.

urlpatterns = [
    path("", medicine_list_view, name="medicines-list"),
    path("create/", medicine_create_view, name="medicines-create"),
    path("<int:pk>/", medicine_detail_view, name="medicine_detail"),
    path("<int:pk>/edit/", medicine_update_view, name="medicine_update"),
    path("<int:pk>/delete/", medicine_delete_view, name="medicine_delete"),
    path("categories/", category_list_view, name="medicines-categories"),
]
