"""
API views for accounts app.

Handles user authentication, registration, and user management.
"""
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, LoginSerializer
from apps.tenants.models import Pharmacy
from apps.tenants.services import SubscriptionService
from apps.tenants.utils import require_user_pharmacy


class UserListView(generics.ListAPIView):
    """
    List all users.
    
    Only accessible by admin users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter users based on user role."""
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        if user.is_admin():
            pharmacy = require_user_pharmacy(user)
            return User.objects.filter(pharmacy=pharmacy)
        # Pharmacy managers can only see themselves
        return User.objects.filter(id=user.id)


class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user profile.
    
    Users can view/update their own profile.
    Admins can view/update any profile.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter based on user permissions."""
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        if user.is_admin():
            pharmacy = require_user_pharmacy(user)
            return User.objects.filter(pharmacy=pharmacy)
        return User.objects.filter(id=user.id)
    
    def get_object(self):
        """Get user object (self or by ID if admin)."""
        user = self.request.user
        user_id = self.kwargs.get('pk')
        
        if user.is_superuser and user_id:
            return User.objects.get(id=user_id)
        if user.is_admin() and user_id:
            pharmacy = require_user_pharmacy(user)
            return User.objects.get(id=user_id, pharmacy=pharmacy)
        return user


class UserCreateView(generics.CreateAPIView):
    """
    Create a new user.
    
    Only accessible by admin users.
    """
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only admins can create users."""
        if self.request.user.is_superuser or self.request.user.is_admin():
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]


def login_view(request):
    """
    User login view.
    
    Handles both API (JSON) and form-based login.
    """
    # Check if this is an API request (JSON)
    if request.content_type == 'application/json' or request.headers.get('Accept') == 'application/json':
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            user_serializer = UserSerializer(user)
            return Response({
                'message': 'Login successful',
                'user': user_serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle form-based login (template)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            return redirect('dashboard')  # Changed from 'dashboard:index' to 'dashboard'
        else:
            messages.error(request, 'Invalid username or password.')
    
    # GET request - show login form
    return render(request, 'accounts/login.html')


def logout_view(request):
    """
    User logout view.
    
    Handles both API and template-based logout.
    """
    logout(request)
    
    # Check if this is an API request
    if request.content_type == 'application/json' or request.headers.get('Accept') == 'application/json':
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    
    # Template-based logout - redirect to login
    messages.success(request, 'You have been logged out successfully.')
    from django.urls import reverse
    return redirect(reverse('login'))


def start_trial_view(request):
    """
    Public onboarding flow:
    - create pharmacy
    - create admin user
    - apply BASIC plan defaults
    - trial period 14 days
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    context = {}
    if request.method == "POST":
        pharmacy_name = (request.POST.get("pharmacy_name") or "").strip()
        username = (request.POST.get("username") or "").strip()
        email = (request.POST.get("email") or "").strip()
        password = request.POST.get("password") or ""
        password_confirm = request.POST.get("password_confirm") or ""

        errors = {}
        if not pharmacy_name:
            errors["pharmacy_name"] = "Pharmacy name is required."
        if not username:
            errors["username"] = "Username is required."
        if not email:
            errors["email"] = "Email is required."
        if not password:
            errors["password"] = "Password is required."
        if password and len(password) < 8:
            errors["password"] = "Password must be at least 8 characters."
        if password != password_confirm:
            errors["password_confirm"] = "Passwords do not match."
        if username and User.objects.filter(username=username).exists():
            errors["username"] = "Username already exists."
        if email and User.objects.filter(email=email).exists():
            errors["email"] = "Email already exists."

        if errors:
            context["errors"] = errors
            context["form"] = {
                "pharmacy_name": pharmacy_name,
                "username": username,
                "email": email,
            }
            return render(request, "accounts/start_trial.html", context, status=400)

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=User.ROLE_ADMIN,
                is_staff=True,
            )
            trial_start = timezone.now()
            pharmacy = Pharmacy.objects.create(
                name=pharmacy_name,
                owner=user,
                plan_type=Pharmacy.PlanType.BASIC,
                subscription_start=trial_start,
                subscription_end=trial_start + timedelta(days=14),
                is_active=True,
            )
            SubscriptionService.apply_plan_defaults(pharmacy, plan_type=Pharmacy.PlanType.BASIC)
            user.pharmacy = pharmacy
            user.save(update_fields=["pharmacy"])

        login(request, user)
        messages.success(request, "Trial started successfully. Welcome to PharmacyAI.")
        return redirect("dashboard")

    return render(request, "accounts/start_trial.html", context)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    """
    Get current authenticated user information.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)
