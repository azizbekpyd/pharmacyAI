# Frontend Dashboard Documentation

## Overview

The Pharmacy Analytic AI frontend is built using Django templates with Tailwind CSS for a modern, professional admin dashboard design.

## Technology Stack

- **Django Templates**: Server-side rendering
- **Tailwind CSS**: Utility-first CSS framework (via CDN)
- **Chart.js**: Data visualization library
- **Font Awesome**: Icon library
- **Vanilla JavaScript**: For API interactions

## Project Structure

```
templates/
├── base.html                    # Base template with sidebar and navigation
├── accounts/
│   └── login.html              # Login page
├── dashboard/
│   └── index.html              # Main dashboard overview
├── medicines/
│   └── list.html               # Medicines management
├── sales/
│   ├── list.html               # Sales records
│   └── analytics.html          # Sales analytics
└── inventory/
    ├── list.html                # Inventory monitoring
    └── reorder_recommendations.html  # Reorder alerts
```

## Features

### 1. Authentication
- **Login Page**: Beautiful gradient design with form validation
- **Session Management**: Django session-based authentication
- **Auto-redirect**: Redirects to dashboard after login

### 2. Dashboard Overview
- **Stats Cards**: Total sales, revenue, medicines, low stock alerts
- **Charts**: Sales trends and category distribution
- **Fast/Slow Moving**: Top and bottom performing medicines
- **Recent Sales**: Latest transactions
- **Alerts**: Reorder recommendations and expiry alerts

### 3. Medicines Management
- **List View**: Table with search, filter, and pagination
- **Filters**: By category, expiry status, stock level
- **Actions**: Edit and delete medicines
- **Real-time Updates**: Fetches data from API

### 4. Sales Management
- **Sales List**: All sales records with date filtering
- **Analytics Page**: Comprehensive charts and metrics
- **Forecasting**: Demand forecasting visualization

### 5. Inventory Management
- **Stock Monitoring**: Current stock levels with status indicators
- **Reorder Recommendations**: Automatic suggestions with approve/reject
- **Stock Updates**: Quick stock level updates

## Design Features

### Responsive Design
- Mobile-friendly sidebar with toggle
- Responsive grid layouts
- Touch-friendly buttons and inputs

### Color Scheme
- **Primary**: Blue (#3B82F6)
- **Success**: Green (#22C55E)
- **Warning**: Orange/Yellow (#F59E0B)
- **Danger**: Red (#EF4444)
- **Dark Sidebar**: Gray-900 (#111827)

### UI Components
- **Cards**: White cards with shadow for content sections
- **Tables**: Clean, bordered tables with hover effects
- **Buttons**: Rounded buttons with hover states
- **Forms**: Styled inputs with focus states
- **Charts**: Chart.js integration for data visualization

## API Integration

All frontend pages fetch data from the REST API endpoints:

```javascript
// Example API call
async function loadData() {
    const response = await fetch('/api/medicines/medicines/');
    const data = await response.json();
    // Render data...
}
```

### CSRF Token Handling
For POST/PUT/DELETE requests, CSRF tokens are included:

```javascript
function getCookie(name) {
    // Extract CSRF token from cookies
}

fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCookie('csrftoken')
    }
});
```

## Navigation

### Sidebar Menu
- Dashboard
- Medicines
- Sales
- Analytics
- Inventory
- Reorder Alerts
- Admin Panel (Admin only)

### Active State
Current page is highlighted in the sidebar using URL matching.

## Charts & Visualizations

### Chart.js Integration
- **Line Charts**: Sales trends over time
- **Doughnut Charts**: Category distribution
- **Bar Charts**: Comparison data

### Example Chart Setup
```javascript
new Chart(ctx, {
    type: 'line',
    data: {
        labels: [...],
        datasets: [...]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false
    }
});
```

## User Experience

### Loading States
- Spinner icons during data loading
- "Loading..." messages in tables
- Smooth transitions

### Error Handling
- Try-catch blocks for API calls
- User-friendly error messages
- Console logging for debugging

### Real-time Updates
- Auto-refresh on actions (create, update, delete)
- Pagination for large datasets
- Search and filter without page reload

## Customization

### Adding New Pages
1. Create template in appropriate app folder
2. Add view in `views_template.py`
3. Add URL in `urls_template.py`
4. Add navigation link in `base.html`

### Styling
- Tailwind utility classes for styling
- Custom CSS in `<style>` tags if needed
- Consistent color scheme throughout

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Responsive design for mobile devices
- Progressive enhancement approach

## Performance

- CDN resources for faster loading
- Lazy loading of charts
- Efficient API calls with pagination
- Minimal JavaScript for better performance

## Security

- CSRF protection on all forms
- Authentication required for all pages
- Role-based access control
- Secure API endpoints

## Future Enhancements

Potential improvements:
1. Real-time updates with WebSockets
2. Export functionality (PDF/Excel)
3. Advanced filtering options
4. Bulk operations
5. Dark mode toggle
6. Customizable dashboard widgets
7. Print-friendly views
8. Data export features
