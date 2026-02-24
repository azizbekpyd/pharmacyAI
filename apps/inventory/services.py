"""
Inventory management services.

This module contains business logic for inventory management and reorder recommendations.
"""
from django.db.models import F
from django.utils import timezone
from .models import Inventory, ReorderRecommendation
from apps.medicines.models import Medicine
from apps.sales.services import DemandForecastingService


class InventoryService:
    """
    Service class for inventory management.
    
    Provides methods for generating reorder recommendations and managing stock levels.
    """
    
    @staticmethod
    def generate_reorder_recommendations(pharmacy):
        """
        Generate automatic reorder recommendations.
        
        Creates recommendations for medicines that:
        1. Have current_stock < min_stock_level
        2. Don't already have a pending recommendation
        
        Uses demand forecasting to calculate recommended quantity.
        
        Returns:
            list: List of ReorderRecommendation objects
        """
        recommendations = []
        
        # Get all inventories that need reordering
        inventories = Inventory.objects.filter(
            pharmacy=pharmacy,
            current_stock__lt=F('min_stock_level')
        ).select_related('medicine')
        
        # Get existing pending recommendations
        existing_recommendations = ReorderRecommendation.objects.filter(
            pharmacy=pharmacy,
            status='PENDING'
        ).values_list('medicine_id', flat=True)
        
        for inventory in inventories:
            # Skip if already has pending recommendation
            if inventory.medicine.id in existing_recommendations:
                continue
            
            # Calculate recommended quantity using enhanced forecasting
            # Try multiple methods and use the average for better accuracy
            forecast_methods = ['sma', 'exponential', 'weighted']
            forecasted_quantities = []
            
            for method in forecast_methods:
                try:
                    forecast = DemandForecastingService.get_forecast(
                        days=30,
                        medicine_id=inventory.medicine.id,
                        method=method,
                        pharmacy=pharmacy,
                    )
                    
                    if forecast['forecasts']:
                        forecast_data = forecast['forecasts'][0]
                        forecasted_quantity = forecast_data['forecast']['forecasted_quantity']
                        if forecasted_quantity > 0:
                            forecasted_quantities.append(forecasted_quantity)
                except:
                    continue
            
            if forecasted_quantities:
                # Use average of multiple forecasting methods
                avg_forecasted_quantity = sum(forecasted_quantities) / len(forecasted_quantities)
                # Add safety stock (20% of max_stock_level)
                safety_stock = int(inventory.max_stock_level * 0.2)
                recommended_quantity = max(
                    inventory.get_reorder_quantity(),  # At least fill to max_stock_level
                    int(avg_forecasted_quantity) + safety_stock
                )
            else:
                # Fallback to standard reorder quantity
                recommended_quantity = inventory.get_reorder_quantity()
            
            # Determine priority based on stock level
            stock_percentage = inventory.stock_percentage()
            if stock_percentage < 10:
                priority = 'URGENT'
            elif stock_percentage < 25:
                priority = 'HIGH'
            elif stock_percentage < 50:
                priority = 'MEDIUM'
            else:
                priority = 'LOW'
            
            # Create recommendation
            reason = f"Current stock ({inventory.current_stock}) is below minimum level ({inventory.min_stock_level})"
            
            recommendation = ReorderRecommendation.objects.create(
                medicine=inventory.medicine,
                pharmacy=pharmacy,
                recommended_quantity=recommended_quantity,
                reason=reason,
                priority=priority,
                status='PENDING'
            )
            
            recommendations.append(recommendation)
        
        return recommendations
