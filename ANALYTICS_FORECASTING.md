# Analytics & Forecasting Documentation

## Overview

The Pharmacy Analytic AI system includes comprehensive analytics and forecasting capabilities to help pharmacies make data-driven decisions.

---

## Sales Analytics Service

### Core Analytics Methods

#### 1. `get_analytics(start_date, end_date)`
Comprehensive sales analytics including:
- **Summary Metrics**: Total sales, revenue, averages, min/max
- **Fast-moving Medicines**: Top-selling medicines
- **Slow-moving Medicines**: Medicines with low sales
- **Daily Trends**: Day-by-day sales breakdown
- **Monthly Trends**: Month-by-month sales analysis
- **Category Analytics**: Sales breakdown by medicine category
- **Peak Hours**: Hourly sales patterns
- **Growth Metrics**: Comparison with previous period

**Example Response:**
```json
{
  "summary": {
    "total_sales": 150,
    "total_amount": 7500.00,
    "average_sale_amount": 50.00,
    "max_sale_amount": 200.00,
    "min_sale_amount": 10.00
  },
  "fast_moving_medicines": [...],
  "slow_moving_medicines": [...],
  "trends": {
    "daily": [...],
    "monthly": [...]
  },
  "category_analytics": [...],
  "peak_hours": [...],
  "growth_metrics": {
    "sales_growth": 15.5,
    "revenue_growth": 20.3
  }
}
```

#### 2. `get_fast_moving_medicines(days, limit)`
Identifies medicines with high sales volume.

**Parameters:**
- `days`: Lookback period (default: 30)
- `limit`: Number of results (default: 10)

**Returns:** List of medicines sorted by total quantity sold

#### 3. `get_slow_moving_medicines(days)`
Identifies medicines with low or no sales.

**Parameters:**
- `days`: Lookback period (default: 90)

**Returns:** List of medicines with sales < 5 units

#### 4. `get_daily_trends(days)`
Daily sales trends for the specified period.

**Returns:** Daily aggregates (sales count, total amount)

#### 5. `get_monthly_trends(start_date, end_date)`
Monthly sales trends for trend analysis.

**Returns:** Monthly aggregates with averages

#### 6. `get_category_analytics(start_date, end_date)`
Sales breakdown by medicine category.

**Returns:** Category-wise metrics (quantity, revenue, sale count)

#### 7. `get_peak_hours(start_date, end_date)`
Identifies peak sales hours for staffing optimization.

**Returns:** Hourly sales data

#### 8. `get_growth_metrics(current_start, current_end, previous_start, previous_end)`
Compares current period with previous period.

**Returns:** Growth percentages for sales count and revenue

#### 9. `get_medicine_performance(medicine_id, days)`
Detailed performance metrics for a specific medicine.

**Returns:** Comprehensive metrics including averages and daily rates

---

## Demand Forecasting Service

### Forecasting Methods

The system supports multiple forecasting methods for better accuracy:

#### 1. Simple Moving Average (SMA) - Default
- **Method**: `'sma'`
- **Description**: Calculates average daily sales over historical period
- **Best for**: Stable demand patterns
- **Formula**: `forecast = (total_quantity / lookback_days) × forecast_days`

#### 2. Exponential Smoothing
- **Method**: `'exponential'`
- **Description**: Gives more weight to recent sales data
- **Best for**: Trending data with recent changes
- **Parameters**: `alpha` (smoothing factor, default: 0.3)
- **Formula**: `smoothed[t] = alpha × actual[t] + (1-alpha) × smoothed[t-1]`

#### 3. Trend Analysis
- **Method**: `'trend'`
- **Description**: Uses linear regression to identify trends
- **Best for**: Data with clear upward/downward trends
- **Formula**: Linear regression on weekly sales data

#### 4. Weighted Moving Average
- **Method**: `'weighted'`
- **Description**: Gives more weight to recent periods
- **Best for**: Seasonal patterns or recent changes
- **Formula**: Weighted average with linear weights

### Core Forecasting Methods

#### `get_forecast(days, medicine_id, method)`
Get demand forecast using specified method.

**Parameters:**
- `days`: Forecast period (default: 30)
- `medicine_id`: Specific medicine (optional)
- `method`: Forecasting method - 'sma', 'exponential', 'trend', 'weighted'

**Example:**
```python
forecast = DemandForecastingService.get_forecast(
    days=30,
    medicine_id=1,
    method='exponential'
)
```

#### `get_forecast_comparison(medicine_id, days)`
Compare all forecasting methods for a medicine.

**Returns:** Forecasts from all methods for comparison

---

## Utility Functions

### Sales Utilities (`apps/sales/utils.py`)

#### `format_currency(amount)`
Format amount as currency string.

#### `format_percentage(value, total)`
Calculate and format percentage.

#### `calculate_sales_velocity(medicine_id, days)`
Calculate sales velocity (units per day).

#### `get_top_performers(limit, days, metric)`
Get top performing medicines by:
- `quantity`: Total quantity sold
- `revenue`: Total revenue
- `frequency`: Number of sales

#### `calculate_inventory_turnover(medicine_id, days)`
Calculate inventory turnover rate.

#### `generate_sales_summary(start_date, end_date)`
Generate comprehensive sales summary report.

---

## API Endpoints

### Enhanced Analytics Endpoints

#### GET `/api/sales/sales/analytics/`
Comprehensive sales analytics with all metrics.

**Query Parameters:**
- `start_date`: Start date (ISO format)
- `end_date`: End date (ISO format)

#### GET `/api/sales/sales/category_analytics/`
Category-wise sales analytics.

#### GET `/api/sales/sales/monthly_trends/`
Monthly sales trends.

#### GET `/api/sales/sales/medicine_performance/`
Detailed medicine performance metrics.

**Query Parameters:**
- `medicine_id`: Medicine ID (required)
- `days`: Analysis period (default: 30)

### Enhanced Forecasting Endpoints

#### GET `/api/sales/sales/forecast/`
Demand forecasting with method selection.

**Query Parameters:**
- `days`: Forecast period (default: 30)
- `medicine_id`: Medicine ID (optional)
- `method`: Forecasting method - 'sma', 'exponential', 'trend', 'weighted'

#### GET `/api/sales/sales/forecast_comparison/`
Compare all forecasting methods.

**Query Parameters:**
- `medicine_id`: Medicine ID (required)
- `days`: Forecast period (default: 30)

---

## Integration with Inventory Management

The enhanced forecasting is integrated with inventory reorder recommendations:

1. **Multi-Method Forecasting**: Uses average of multiple forecasting methods
2. **Safety Stock**: Adds 20% safety stock to forecasted quantity
3. **Priority Calculation**: Based on stock percentage and forecast urgency
4. **Automatic Generation**: Recommendations generated automatically when stock is low

**Location:** `apps/inventory/services.py` - `InventoryService.generate_reorder_recommendations()`

---

## Usage Examples

### Example 1: Get Comprehensive Analytics
```python
from apps.sales.services import SalesAnalyticsService
from datetime import datetime, timedelta
from django.utils import timezone

end_date = timezone.now()
start_date = end_date - timedelta(days=30)

analytics = SalesAnalyticsService.get_analytics(
    start_date=start_date,
    end_date=end_date
)

print(f"Total Revenue: ${analytics['summary']['total_amount']}")
print(f"Sales Growth: {analytics['growth_metrics']['sales_growth']}%")
```

### Example 2: Forecast with Exponential Smoothing
```python
from apps.sales.services import DemandForecastingService

forecast = DemandForecastingService.get_forecast(
    days=30,
    medicine_id=1,
    method='exponential'
)

forecast_data = forecast['forecasts'][0]
print(f"Forecasted Quantity: {forecast_data['forecast']['forecasted_quantity']}")
```

### Example 3: Compare Forecasting Methods
```python
from apps.sales.services import DemandForecastingService

comparison = DemandForecastingService.get_forecast_comparison(
    medicine_id=1,
    days=30
)

for method, data in comparison['methods'].items():
    print(f"{method}: {data['forecast']['forecasted_quantity']}")
```

---

## Performance Considerations

1. **Database Optimization**: Uses `select_related` and `prefetch_related` for efficient queries
2. **Caching**: Consider implementing caching for frequently accessed analytics
3. **Pagination**: Large datasets are paginated automatically
4. **Indexes**: Database indexes on date fields for faster queries

---

## Future Enhancements

Potential improvements for future versions:

1. **Machine Learning**: Integration with ML models for more accurate forecasting
2. **Seasonal Adjustments**: Automatic seasonal pattern detection
3. **External Data**: Integration with weather, events, or other external factors
4. **Real-time Analytics**: WebSocket-based real-time dashboard updates
5. **Custom Reports**: User-defined report generation
6. **Export Functionality**: PDF/Excel export of analytics reports

---

## Notes

- **Database Compatibility**: Date functions use SQLite syntax (`strftime`). For PostgreSQL, modify to use `EXTRACT` or `DATE_TRUNC`.
- **Time Zones**: All dates are handled in UTC. Adjust for local time zones in frontend.
- **Data Requirements**: Forecasting accuracy improves with more historical data (minimum 30 days recommended).
