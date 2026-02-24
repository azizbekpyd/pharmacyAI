# API Documentation

## Base URL
All API endpoints are prefixed with `/api/`

## Authentication
Most endpoints require authentication. Use session-based authentication (login via `/api/auth/login/`).

---

## Accounts API (`/api/auth/`)

### Login
- **POST** `/api/auth/login/`
- **Body:**
  ```json
  {
    "username": "admin",
    "password": "password123"
  }
  ```
- **Response:** User object with session cookie

### Logout
- **POST** `/api/auth/logout/`
- **Response:** Success message

### Current User
- **GET** `/api/auth/user/`
- **Response:** Current authenticated user information

### User Management
- **GET** `/api/auth/users/` - List all users (Admin only)
- **POST** `/api/auth/users/create/` - Create new user (Admin only)
- **GET** `/api/auth/users/{id}/` - Get user details
- **PUT/PATCH** `/api/auth/users/{id}/` - Update user

---

## Medicines API (`/api/medicines/`)

### Categories
- **GET** `/api/medicines/categories/` - List all categories
- **POST** `/api/medicines/categories/` - Create category
- **GET** `/api/medicines/categories/{id}/` - Get category details
- **PUT/PATCH** `/api/medicines/categories/{id}/` - Update category
- **DELETE** `/api/medicines/categories/{id}/` - Delete category

### Medicines
- **GET** `/api/medicines/medicines/` - List all medicines
  - Query params: `category`, `expiring_soon`, `expired`, `low_stock`, `search`, `ordering`
- **POST** `/api/medicines/medicines/` - Create medicine
- **GET** `/api/medicines/medicines/{id}/` - Get medicine details
- **PUT/PATCH** `/api/medicines/medicines/{id}/` - Update medicine
- **DELETE** `/api/medicines/medicines/{id}/` - Delete medicine

### Medicine Alerts
- **GET** `/api/medicines/medicines/expiring_soon/` - Get medicines expiring soon
  - Query params: `days` (default: 30)
- **GET** `/api/medicines/medicines/expired/` - Get expired medicines

---

## Sales API (`/api/sales/`)

### Sales
- **GET** `/api/sales/sales/` - List all sales
  - Query params: `start_date`, `end_date`, `user`, `search`, `ordering`
- **POST** `/api/sales/sales/` - Create new sale
  - **Body:**
    ```json
    {
      "date": "2024-01-15T10:30:00Z",
      "user": 1,
      "notes": "Optional notes",
      "items": [
        {
          "medicine_id": 1,
          "quantity": 2,
          "unit_price": 10.50
        }
      ]
    }
    ```
- **GET** `/api/sales/sales/{id}/` - Get sale details
- **PUT/PATCH** `/api/sales/sales/{id}/` - Update sale
- **DELETE** `/api/sales/sales/{id}/` - Delete sale

### Sales Analytics
- **GET** `/api/sales/sales/analytics/` - Get comprehensive sales analytics
  - Query params: `start_date`, `end_date`
  - **Response:**
    ```json
    {
      "summary": {
        "total_sales": 100,
        "total_amount": 5000.00,
        "average_sale_amount": 50.00
      },
      "fast_moving_medicines": [...],
      "slow_moving_medicines": [...],
      "trends": [...]
    }
    ```

### Demand Forecasting
- **GET** `/api/sales/sales/forecast/` - Get demand forecast
  - Query params: `days` (default: 30), `medicine_id` (optional)
  - **Response:** Forecasted demand for medicines

### Fast/Slow Moving Medicines
- **GET** `/api/sales/sales/fast_moving/` - Get fast-moving medicines
  - Query params: `days` (default: 30), `limit` (default: 10)
- **GET** `/api/sales/sales/slow_moving/` - Get slow-moving medicines
  - Query params: `days` (default: 90)

---

## Inventory API (`/api/inventory/`)

### Inventory
- **GET** `/api/inventory/inventory/` - List all inventory records
  - Query params: `needs_reorder`, `low_stock`, `search`, `ordering`
- **POST** `/api/inventory/inventory/` - Create inventory record
- **GET** `/api/inventory/inventory/{id}/` - Get inventory details
- **PUT/PATCH** `/api/inventory/inventory/{id}/` - Update inventory
- **DELETE** `/api/inventory/inventory/{id}/` - Delete inventory

### Stock Management
- **POST** `/api/inventory/inventory/{id}/update_stock/` - Update stock level
  - **Body:**
    ```json
    {
      "quantity": 100,
      "operation": "set"  // "set", "add", or "subtract"
    }
    ```

### Reorder Recommendations
- **GET** `/api/inventory/inventory/reorder_recommendations/` - Get automatic reorder recommendations
- **GET** `/api/inventory/reorder-recommendations/` - List all recommendations
  - Query params: `status`, `priority`, `search`, `ordering`
- **POST** `/api/inventory/reorder-recommendations/` - Create recommendation
- **GET** `/api/inventory/reorder-recommendations/{id}/` - Get recommendation details
- **PUT/PATCH** `/api/inventory/reorder-recommendations/{id}/` - Update recommendation
- **POST** `/api/inventory/reorder-recommendations/{id}/approve/` - Approve recommendation
- **POST** `/api/inventory/reorder-recommendations/{id}/reject/` - Reject recommendation

---

## POS Integration API (`/api/pos/`)

### Receive Sales Data
- **POST** `/api/pos/sales/` - Receive single sale from POS
  - **Body:**
    ```json
    {
      "sale_id": "POS-12345",
      "date": "2024-01-15T10:30:00Z",
      "items": [
        {
          "medicine_sku": "MED001",
          "quantity": 2,
          "unit_price": 10.50
        }
      ],
      "notes": "Optional notes"
    }
    ```

### Bulk Sales
- **POST** `/api/pos/sales/bulk/` - Receive multiple sales from POS
  - **Body:**
    ```json
    {
      "sales": [
        {
          "sale_id": "POS-12345",
          "date": "2024-01-15T10:30:00Z",
          "items": [...]
        }
      ]
    }
    ```

### CSV Import
- **POST** `/api/pos/import-csv/` - Import sales from CSV file
  - **Form Data:** `file` (CSV file)
  - **CSV Format:**
    ```csv
    date,medicine_sku,quantity,unit_price,notes
    2024-01-15 10:30:00,MED001,2,10.50,First sale
    2024-01-15 11:00:00,MED002,1,25.00,Second sale
    ```

---

## Common Query Parameters

### Pagination
All list endpoints support pagination:
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

### Search
Endpoints with search support:
- `search` - Search term (searches in configured fields)

### Ordering
Endpoints with ordering support:
- `ordering` - Field to order by (prefix with `-` for descending)
- Example: `?ordering=-date` (newest first)

### Filtering
Various endpoints support filtering via query parameters. See individual endpoint documentation above.

---

## Error Responses

All endpoints return standard HTTP status codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error response format:
```json
{
  "error": "Error message",
  "details": {...}
}
```
