"""
Template views for inventory app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def inventory_list_view(request):
    """Render inventory list page."""
    return render(request, 'inventory/list.html')


@login_required
def reorder_recommendations_view(request):
    """Render reorder recommendations page."""
    return render(request, 'inventory/reorder_recommendations.html')
