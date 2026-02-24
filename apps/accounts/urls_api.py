"""
API URL configuration for accounts app.
"""
from django.urls import path
from .views import (
    UserListView, UserDetailView, UserCreateView,
    login_view, logout_view, current_user_view
)

# API URLs - used at 'api/auth/' prefix
urlpatterns = [
    # Authentication endpoints
    path('login/', login_view, name='api-login'),
    path('logout/', logout_view, name='api-logout'),
    path('user/', current_user_view, name='api-current-user'),
    
    # User management endpoints
    path('users/', UserListView.as_view(), name='api-user-list'),
    path('users/create/', UserCreateView.as_view(), name='api-user-create'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='api-user-detail'),
]
