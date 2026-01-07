"""
API Serializers for user authentication and profile management
All serializers follow standard response format for consistency
"""

from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .validators import (
    validate_password_strength,
    validate_email_format,
    validate_name,
    validate_date_of_birth,
    validate_password_match,
    validate_profile_picture
)
from .exceptions import (
    InvalidCredentialsException,
    EmailNotVerifiedException,
    PasswordMismatchException,
    EmailAlreadyExistsException,
)
from .utils import validate_age

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration (signup)
    
    Required fields:
    - email: User's email address
    - password: User's password
    - confirm_password: Password confirmation
    """
    
    # Extra field for password confirmation (not in model)
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
        help_text="User's password (min 8 chars, must include uppercase, lowercase, number, special char)"
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'confirm_password', 'first_name', 'last_name']
    
    def validate_email(self, value):
        """Validate email format and check if it already exists"""
        # Validate email format
        try:
            validate_email_format(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
        
        # Check if email already exists
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        
        return value.lower()
    
    def validate_password(self, value):
        """Validate password strength"""
        try:
            # Use custom validator
            validate_password_strength(value)
            
            # Also use Django's built-in validators
            django_validate_password(value)
            
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
    
    def validate(self, attrs):
        """Validate that passwords match"""
        try:
            validate_password_match(attrs['password'], attrs['confirm_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'confirm_password': str(e)})
        
        return attrs
    
    def create(self, validated_data):
        """Create new user and send OTP"""
        validated_data.pop('confirm_password')
        email = validated_data.pop('email')
        password = validated_data.pop('password')

        user = User.objects.create_user(email, password, **validated_data)
        user.is_active = False  # User is inactive until OTP verification
        
        # Generate and send OTP
        from .utils import generate_otp, send_otp_email
        otp = generate_otp()
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save(update_fields=['otp', 'otp_created_at', 'is_active'])
        send_otp_email(user, otp)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    
    Required fields:
    - email: User's email address
    - password: User's password
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="User's email address"
    )
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="User's password"
    )
    
    def validate(self, attrs):
        """Validate user credentials"""
        email = attrs.get('email', '').lower()
        password = attrs.get('password')
        
        if email and password:
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise InvalidCredentialsException("Invalid email or password")
            
            # Check if user is active
            if not user.is_active:
                raise serializers.ValidationError("User account is disabled.")
            
            # Authenticate user
            user = authenticate(email=email, password=password)
            
            if not user:
                raise InvalidCredentialsException("Invalid email or password")
            
            # Check if email is verified (optional - uncomment if you want to enforce)
            # if not user.is_email_verified:
            #     raise EmailNotVerifiedException()
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")


class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification
    """
    
    token = serializers.CharField(
        required=True,
        help_text="Email verification token sent to user's email"
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting password reset
    """
    
    email = serializers.EmailField(
        required=True,
        help_text="Email address of the account to reset password"
    )
    
    def validate_email(self, value):
        """Check if user with this email exists"""
        value = value.lower()
        
        if not User.objects.filter(email=value).exists():
            # For security, don't reveal if email exists or not
            # Just return the value, handle silently in view
            pass
        
        return value


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
        """Validate password strength"""
        try:
            validate_password_strength(value)
            django_validate_password(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
    
    def validate(self, attrs):
        """Validate that passwords match"""
        try:
            validate_password_match(attrs['password'], attrs['confirm_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'confirm_password': str(e)})
        
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for changing password (authenticated user)
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
        """Validate new password strength"""
        try:
            validate_password_strength(value)
            django_validate_password(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
    
    def validate(self, attrs):
        """Validate passwords"""
        # Check if new passwords match
        try:
            validate_password_match(attrs['new_password'], attrs['confirm_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'confirm_password': str(e)})
        
        # Check if new password is different from old password
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': 'New password must be different from old password.'
            })
        
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile (read and update)
    """
    
    age = serializers.SerializerMethodField(
        read_only=True,
        help_text="User's age calculated from date of birth"
    )

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'date_of_birth',
            'gender',
            'occupation',
            'country',
            'age',
            'bio',
            'profile_picture',
            'is_email_verified',
            'is_subscribed',
            'date_joined',
            'last_login',
        ]
        read_only_fields = [
            'id',
            'email',
            'is_email_verified',
            'is_subscribed',
            'date_joined',
            'last_login',
        ]
    
    def get_age(self, obj):
        """Calculate age from date of birth"""
        from .utils import calculate_age
        return calculate_age(obj.date_of_birth)

    def validate_first_name(self, value):
        """Validate user's first name"""
        try:
            validate_name(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))

    def validate_last_name(self, value):
        """Validate user's last name"""
        try:
            validate_name(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        try:
            validate_date_of_birth(value)
            
            if not validate_age(value, min_age=13):
                raise serializers.ValidationError(
                    "You must be at least 13 years old."
                )
            
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_profile_picture(self, value):
        """Validate profile picture"""
        if value:
            try:
                validate_profile_picture(value)
                return value
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile (partial updates allowed)
    """
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'date_of_birth', 'gender', 'occupation', 'country', 'bio', 'profile_picture']
    
    def validate_first_name(self, value):
        """Validate user's first name"""
        try:
            validate_name(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_last_name(self, value):
        """Validate user's last name"""
        try:
            validate_name(value)
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        try:
            validate_date_of_birth(value)
            
            if not validate_age(value, min_age=13):
                raise serializers.ValidationError(
                    "You must be at least 13 years old."
                )
            
            return value
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate_profile_picture(self, value):
        """Validate profile picture"""
        if value:
            try:
                validate_profile_picture(value)
                return value
            except DjangoValidationError as e:
                raise serializers.ValidationError(str(e))
        return value


class AccountDeleteSerializer(serializers.Serializer):
    """
    Serializer for account deletion confirmation
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Enter your password to confirm account deletion"
    )
    
    confirm_deletion = serializers.BooleanField(
        required=True,
        help_text="Must be set to true to confirm deletion"
    )
    
    def validate_confirm_deletion(self, value):
        """Ensure user confirms deletion"""
        if not value:
            raise serializers.ValidationError(
                "You must confirm that you want to delete your account."
            )
        return value


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Serializer for token refresh response
    """
    access = serializers.CharField(help_text="New access token")
    refresh = serializers.CharField(help_text="New refresh token (if rotation enabled)")


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for OTP verification
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)

class PasswordResetOTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP for password reset
    """
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=4)

class ResendOTPSerializer(serializers.Serializer):
    """
    Serializer for resending OTP
    """
    email = serializers.EmailField()

class TokenVerifyResponseSerializer(serializers.Serializer):
    """
    Serializer for token verification response
    """
    valid = serializers.BooleanField(help_text="Whether token is valid")
    user_id = serializers.UUIDField(help_text="User ID from token", required=False)

class LanguagePreferenceSerializer(serializers.Serializer):
    language = serializers.ChoiceField(choices=[('en', 'English'), ('hi', 'Hindi'), ('pt', 'Portuguese')])

class UserProfileRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'date_of_birth', 'address', 'address_line_2', 'city', 'state', 'zip_code']
