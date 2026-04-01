"""
API Serializers for business account authentication and profile management
"""

from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import BusinessAccount
from .validators import (
    validate_password_strength,
    validate_email_format,
    validate_password_match,
)
from .utils import generate_otp, send_otp_email
from users.exceptions import InvalidCredentialsException


class BusinessAccountRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for business account registration (signup)
    """
    
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Password confirmation"
    )
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Business account's password (min 8 chars, must include uppercase, lowercase, number, special char)"
    )
    
    class Meta:
        model = BusinessAccount
        fields = ['email', 'password', 'confirm_password']
    
    def validate_email(self, value):
        try:
            validate_email_format(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        
        if BusinessAccount.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        
        return value.lower()
    
    def validate_password(self, value):
        try:
            validate_password_strength(value)
            django_validate_password(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
    
    def validate(self, attrs):
        try:
            validate_password_match(attrs['password'], attrs['confirm_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'confirm_password': str(e)})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        business_account = BusinessAccount.objects.create_user(email, password, **validated_data)
        business_account.is_active = False  # Inactive until OTP verification
        
        otp = generate_otp()
        business_account.otp = otp
        business_account.otp_created_at = timezone.now()
        business_account.save(update_fields=['otp', 'otp_created_at', 'is_active'])
        send_otp_email(business_account, otp)
        
        return business_account


class BusinessAccountLoginSerializer(serializers.Serializer):
    """
    Serializer for business account login
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Business account's email address"
    )
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Business account's password"
    )
    
    def validate(self, attrs):
        email = attrs.get('email', '').lower()
        password = attrs.get('password')
        
        if email and password:
            try:
                business_account = BusinessAccount.objects.get(email=email)
            except BusinessAccount.DoesNotExist:
                raise InvalidCredentialsException("Invalid email or password")
            
            if not business_account.is_active:
                raise serializers.ValidationError("Business account is disabled.")
            
            # Authenticate using custom logic for BusinessAccount
            if not business_account.check_password(password):
                raise InvalidCredentialsException("Invalid email or password")
            
            attrs['business_account'] = business_account
            return attrs
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for OTP verification
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)


class ResendOTPSerializer(serializers.Serializer):
    """
    Serializer for resending OTP
    """
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting password reset
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Email address of the business account to reset password"
    )
    
    def validate_email(self, value):
        value = value.lower()
        if not BusinessAccount.objects.filter(email=value).exists():
            pass # For security, don't reveal if email exists or not
        return value


class PasswordResetOTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP for password reset
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for confirming password reset with OTP
    """
    
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="New password"
    )
    
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Password confirmation"
    )
    
    def validate_password(self, value):
        try:
            validate_password_strength(value)
            django_validate_password(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
    
    def validate(self, attrs):
        try:
            validate_password_match(attrs['password'], attrs['confirm_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'confirm_password': str(e)})
        
        return attrs


class BusinessAccountProfileRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for completing business account profile
    """
    class Meta:
        model = BusinessAccount
        fields = [
            'role_position', 'business_name', 'industry_category',
            'business_email', 'website',
            'address', 'address_line_2', 'city', 'state', 'zip_code'
        ]

    def validate_website(self, value):
        """
        Automatically prepend https:// if protocol is missing.
        """
        if value and not value.startswith(('http://', 'https://')):
            return f'https://{value}'
        return value


class BusinessAccountProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for business account profile (read and update)
    """
    class Meta:
        model = BusinessAccount
        fields = [
            'id', 'email', 'role_position', 'business_name', 'industry_category',
            'business_email', 'website',
            'address', 'address_line_2', 'city', 'state', 'zip_code',
            'is_email_verified', 'is_profile_complete', 'date_joined', 'last_login', 'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'is_email_verified', 'is_profile_complete', 'date_joined', 'last_login', 'updated_at'
        ]

    def validate_website(self, value):
        """
        Automatically prepend https:// if protocol is missing.
        """
        if value and not value.startswith(('http://', 'https://')):
            return f'https://{value}'
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing password (authenticated business account)
    """
    
    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Current password"
    )
    
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="New password"
    )
    
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="New password confirmation"
    )
    
    def validate_new_password(self, value):
        try:
            validate_password_strength(value)
            django_validate_password(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
    
    def validate(self, attrs):
        try:
            validate_password_match(attrs['new_password'], attrs['confirm_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'confirm_password': str(e)})
        
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': 'New password must be different from old password.'
            })
        
        return attrs
