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
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, LoginSerializer
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


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    """
    Get current authenticated user information.
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)
