"""
Serializers for accounts app.

Handles serialization/deserialization of User model and authentication data.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User
from apps.tenants.models import Pharmacy
from apps.tenants.services import SubscriptionService


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    
    Used for user profile information and user list views.
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    pharmacy_name = serializers.CharField(source='pharmacy.name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'role_display', 'phone_number', 'pharmacy', 'pharmacy_name', 'is_active',
            'date_joined', 'created_at'
        ]
        read_only_fields = ['id', 'date_joined', 'created_at', 'pharmacy', 'pharmacy_name']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new users.
    
    Includes password field with write-only access.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    pharmacy_id = serializers.PrimaryKeyRelatedField(
        queryset=Pharmacy.objects.all(),
        source="pharmacy",
        write_only=True,
        required=False,
        allow_null=True,
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'role', 'phone_number', 'pharmacy_id'
        ]
    
    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Passwords do not match.'
            })
        return attrs
    
    def create(self, validated_data):
        """Create a new user with hashed password."""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        request = self.context.get("request")

        if request and request.user and request.user.is_authenticated and not request.user.is_superuser:
            validated_data["pharmacy"] = getattr(request.user, "pharmacy", None)
        elif "pharmacy" not in validated_data and request and request.user and request.user.is_authenticated:
            validated_data["pharmacy"] = getattr(request.user, "pharmacy", None)

        pharmacy = validated_data.get("pharmacy")
        if pharmacy is not None and not (request and request.user and request.user.is_authenticated and request.user.is_superuser):
            try:
                SubscriptionService.enforce_limits(pharmacy, SubscriptionService.RESOURCE_USERS)
            except DjangoValidationError as exc:
                if hasattr(exc, "message_dict"):
                    raise serializers.ValidationError(exc.message_dict)
                raise serializers.ValidationError({"subscription": exc.messages})

        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    
    Validates username/email and password.
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Authenticate user with provided credentials."""
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            # Try to authenticate with username or email
            user = authenticate(username=username, password=password)
            if not user:
                # Try email if username fails
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            if not user:
                raise serializers.ValidationError(
                    'Invalid username/email or password.'
                )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'User account is disabled.'
                )
            
            attrs['user'] = user
        else:
            raise serializers.ValidationError(
                'Must include "username" and "password".'
            )
        
        return attrs
