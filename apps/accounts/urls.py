"""
Frontend URL configuration for accounts app.
Used for template-based login.
"""
from django.urls import path
from .views import login_view

# Frontend URLs - used at 'login/' prefix
# Empty path means this will be accessible at '/login/' when included
urlpatterns = [
    path('', login_view, name='login'),  # Accessible at /login/
]

