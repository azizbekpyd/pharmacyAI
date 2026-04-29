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


@login_required
def stock_movements_view(request):
    """Render stock movement ledger page."""
    return render(request, 'inventory/stock_movements.html')


@login_required
def purchases_view(request):
    """Render supplier and purchase order page."""
    return render(request, 'inventory/purchases.html')


@login_required
def activity_log_view(request):
    """Render activity/audit log page."""
    return render(request, 'inventory/activity_log.html')
