# Sales Analytics Template Context

## Overview

The `sales_analytics_view` calculates and passes the following context data to the template:

## Context Keys

### Summary Metrics

1. **`total_sales`** (int)
   - Total number of sales transactions
   - Example: `144`
   - Used in: `{{ total_sales|default:0 }}`

2. **`total_revenue`** (float)
   - Total revenue amount from all sales
   - Example: `7500.50`
   - Used in: `${{ total_revenue|floatformat:2|default:"0.00" }}`

3. **`average_sale`** (float)
   - Average sale amount
   - Example: `52.09`
   - Used in: `${{ average_sale|floatformat:2|default:"0.00" }}`

4. **`growth_percentage`** (float or None)
   - Revenue growth percentage compared to previous period
   - Example: `15.5` or `None`
   - Used in: `{{ growth_percentage|floatformat:1 }}%`

### Sales Trend Data

5. **`sales_trend`** (list of dicts)
   - Daily sales trend data for the last 7 days
   - Format: `[{'day': '2024-01-15', 'total_sales': 5, 'total_amount': 250.00}, ...]`
   - Used for: Template loops and chart rendering
   - Example usage: `{% for item in sales_trend %}{{ item.day }}{% endfor %}`

6. **`sales_trend_json`** (JSON string)
   - Same data as `sales_trend` but as JSON string for JavaScript
   - Used in: `<script>const salesTrendData = {{ sales_trend_json|safe }};</script>`

### Category Distribution

7. **`category_distribution`** (list of dicts)
   - Sales breakdown by medicine category
   - Format: `[{'medicine__category__name': 'Pain Relief', 'total_revenue': 1500.00, 'total_quantity': 100}, ...]`
   - Used for: Template loops and chart rendering
   - Example usage: `{% for cat in category_distribution %}{{ cat.medicine__category__name }}{% endfor %}`

8. **`category_distribution_json`** (JSON string)
   - Same data as `category_distribution` but as JSON string for JavaScript
   - Used in: `<script>const categoryData = {{ category_distribution_json|safe }};</script>`

### Fast & Slow Moving Medicines

9. **`fast_moving_medicines`** (list of dicts)
   - Top 10 medicines by sales quantity (last 30 days)
   - Format: `[{'medicine__id': 1, 'medicine__name': 'Paracetamol', 'medicine__sku': 'MED001', 'total_quantity': 50, 'total_revenue': 275.00, 'sale_count': 25}, ...]`
   - Used in: Template loop to display fast-moving medicines
   - Example usage: `{% for item in fast_moving_medicines %}{{ item.medicine__name }}{% endfor %}`

10. **`slow_moving_medicines`** (list of dicts)
    - Medicines with low or no sales (last 90 days, top 10)
    - Format: `[{'medicine_id': 8, 'medicine_name': 'Antibacterial Cream', 'medicine_sku': 'MED008', 'total_quantity': 2, 'total_revenue': 15.00, 'sale_count': 1}, ...]`
    - Used in: Template loop to display slow-moving medicines
    - Example usage: `{% for item in slow_moving_medicines %}{{ item.medicine_name }}{% endfor %}`

## Template Usage Examples

### Displaying Summary Metrics

```django
<!-- Total Sales -->
{{ total_sales|default:0 }}

<!-- Total Revenue -->
${{ total_revenue|floatformat:2|default:"0.00" }}

<!-- Average Sale -->
${{ average_sale|floatformat:2|default:"0.00" }}

<!-- Growth Percentage -->
{% if growth_percentage != None %}
    {% if growth_percentage >= 0 %}+{% endif %}{{ growth_percentage|floatformat:1 }}%
{% else %}
    N/A
{% endif %}
```

### Displaying Fast Moving Medicines

```django
{% for item in fast_moving_medicines %}
    <div>
        <span>{{ item.medicine__name|default:"N/A" }}</span>
        <span>{{ item.total_quantity|default:0 }} units</span>
    </div>
{% empty %}
    <p>No fast moving medicines</p>
{% endfor %}
```

### Displaying Slow Moving Medicines

```django
{% for item in slow_moving_medicines %}
    <div>
        <span>{{ item.medicine_name|default:"N/A" }}</span>
        <span>{{ item.total_quantity|default:0 }} units</span>
    </div>
{% empty %}
    <p>No slow moving medicines</p>
{% endfor %}
```

### Using JSON Data in JavaScript

```javascript
// Sales Trend Chart
const salesTrendData = {{ sales_trend_json|safe }};
const trendData = JSON.parse(salesTrendData || '[]');
// Use trendData for Chart.js

// Category Distribution Chart
const categoryData = {{ category_distribution_json|safe }};
const catData = JSON.parse(categoryData || '[]');
// Use catData for Chart.js
```

## Data Calculation Logic

All calculations use Django ORM aggregations:

- **Total Sales**: `Sale.objects.filter(...).count()`
- **Total Revenue**: `Sale.objects.filter(...).aggregate(Sum('total_amount'))`
- **Average Sale**: `Sale.objects.filter(...).aggregate(Avg('total_amount'))`
- **Sales Trend**: `Sale.objects.filter(...).extra(select={'day': "date(date)"}).values('day').annotate(...)`
- **Category Distribution**: `SaleItem.objects.filter(...).values('medicine__category__name').annotate(...)`
- **Fast Moving**: `SaleItem.objects.filter(...).values('medicine__name').annotate(Sum('quantity')).order_by('-total_quantity')`
- **Slow Moving**: Medicines with `total_quantity < 5` in the last 90 days

## Notes

- All date calculations default to last 30 days if no date range is provided
- Growth percentage compares current period with previous period of same length
- Fast moving medicines are sorted by total quantity sold (descending)
- Slow moving medicines include medicines with no sales or very low sales (< 5 units)
