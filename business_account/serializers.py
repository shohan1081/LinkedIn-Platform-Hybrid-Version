"""
API Serializers for business account authentication and profile management
"""

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from .models import BusinessAccount, VerificationRequest
from users.models import User
from .validators import (
    validate_password_strength,
    validate_email_format,
    validate_password_match,
)
from .utils import generate_otp, send_otp_email
from users.exceptions import InvalidCredentialsException

class UserSimpleSerializer(serializers.ModelSerializer):
    """
    Simple serializer for User to be used in verification-related lists
    """
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'profile_picture', 'is_verified']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and instance.profile_picture:
            representation['profile_picture'] = request.build_absolute_uri(instance.profile_picture.url)
        return representation


class VerificationRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for VerificationRequest
    """
    user_details = UserSimpleSerializer(source='user', read_only=True)
    business_name = serializers.CharField(source='business_account.business_name', read_only=True)

    class Meta:
        model = VerificationRequest
        fields = [
            'id', 'user', 'business_account', 'status', 
            'created_at', 'updated_at', 'user_details', 'business_name'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at', 'user_details', 'business_name']

    def validate(self, attrs):
        # Additional validation can be added here if needed
        return attrs


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
    website = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = BusinessAccount
        fields = [
            'role_position', 'business_name', 'industry_category',
            'business_email', 'website', 'headline', 'profile_picture', 'cover_photo', 'about',
            'address', 'address_line_2', 'city', 'state', 'zip_code'
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            if instance.profile_picture:
                representation['profile_picture'] = request.build_absolute_uri(instance.profile_picture.url)
            if instance.cover_photo:
                representation['cover_photo'] = request.build_absolute_uri(instance.cover_photo.url)
        return representation

    def validate_website(self, value):
        """
        Automatically prepend https:// if protocol is missing and validate format.
        """
        if not value:
            return value
            
        if not value.startswith(('http://', 'https://')):
            value = f'https://{value}'
            
        # Use Django's URL validator to ensure it's actually valid after prepending
        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError as DjangoValidationError
        validate_url = URLValidator()
        try:
            validate_url(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid URL.")
            
        return value


class BusinessAccountProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for business account profile (read and update)
    """
    website = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    account_type = serializers.SerializerMethodField()
    author_id = serializers.SerializerMethodField()

    class Meta:
        model = BusinessAccount
        fields = [
            'id', 'author_id', 'email', 'role_position', 'business_name', 'industry_category',
            'business_email', 'website', 'headline', 'about', 'profile_picture', 'cover_photo',
            'address', 'address_line_2', 'city', 'state', 'zip_code',
            'is_email_verified', 'is_profile_complete', 'account_type',
            'date_joined', 'last_login', 'updated_at'
        ]
        read_only_fields = [
            'id', 'author_id', 'email', 'is_email_verified', 'is_profile_complete', 'date_joined', 'last_login', 'updated_at'
        ]

    def get_author_id(self, obj):
        return str(obj.id)

    def get_account_type(self, obj):
        return 'business'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request:
            if instance.profile_picture:
                representation['profile_picture'] = request.build_absolute_uri(instance.profile_picture.url)
            if instance.cover_photo:
                representation['cover_photo'] = request.build_absolute_uri(instance.cover_photo.url)
        return representation

    def validate_website(self, value):
        """
        Automatically prepend https:// if protocol is missing and validate format.
        """
        if not value:
            return value
            
        if not value.startswith(('http://', 'https://')):
            value = f'https://{value}'
            
        from django.core.validators import URLValidator
        validate_url = URLValidator()
        try:
            validate_url(value)
        except:
            raise serializers.ValidationError("Enter a valid URL.")
            
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


class PublicBusinessProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for viewing a business's public profile
    """
    recommendations = serializers.SerializerMethodField()
    posts = serializers.SerializerMethodField()

    class Meta:
        model = BusinessAccount
        fields = [
            'id', 'business_name', 'headline', 'about', 'industry_category', 
            'website', 'city', 'state', 'profile_picture', 
            'cover_photo', 'recommendations', 'posts'
        ]

    def get_posts(self, obj):
        from posts.models import NeedPost, OfferPost
        from posts.serializers import NeedPostSerializer, OfferPostSerializer
        
        business_ct = ContentType.objects.get_for_model(BusinessAccount)
        need_posts = NeedPost.objects.filter(author_content_type=business_ct, author_object_id=obj.id)
        offer_posts = OfferPost.objects.filter(author_content_type=business_ct, author_object_id=obj.id)
        
        return {
            'need_posts': NeedPostSerializer(need_posts, many=True, context=self.context).data,
            'offer_posts': OfferPostSerializer(offer_posts, many=True, context=self.context).data
        }

    def get_recommendations(self, obj):
        from users.models import Recommendation
        from users.serializers import RecommendationSerializer
        
        business_ct = ContentType.objects.get_for_model(BusinessAccount)
        recommendations = Recommendation.objects.filter(
            receiver_content_type=business_ct,
            receiver_object_id=obj.id
        )
        return RecommendationSerializer(recommendations, many=True, context=self.context).data
