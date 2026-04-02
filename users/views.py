from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth import get_user_model # Move get_user_model here

# Create your views here.
"""
API Views for user authentication and profile management
All views return standardized response format
"""

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.contrib.auth import get_user_model
#from progress.utils import mark_user_login
from django.utils import timezone
from django.conf import settings
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetOTPVerifySerializer,
    ResendOTPSerializer,
    VerifyOTPSerializer,
    PasswordChangeSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    AccountDeleteSerializer,
    LanguagePreferenceSerializer,
    UserProfileRegistrationSerializer,
    MultiModelTokenRefreshSerializer,
)
from .utils import (
    send_welcome_email,
    send_account_deletion_email,
    get_client_ip,
    get_user_agent,
)
from .models import UserLoginHistory, AccountDeletionRequest, ProfileDataDeletionRequest
from django.shortcuts import render

@csrf_exempt
def delete_profile_data_request_view(request):
    return render(request, 'users/delete_profile_data_request.html')

@method_decorator(csrf_exempt, name='dispatch')
class ProfileDataDeletionAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return render(request, 'users/delete_profile_data_request.html', {'error': 'Email is required.'})

        user = User.objects.filter(email=email).first()
        if user:
            deletion_request, created = ProfileDataDeletionRequest.objects.get_or_create(user=user, defaults={'email': email})
            
            verification_link = request.build_absolute_uri(
                reverse('users:verify_profile_data_deletion', kwargs={'token': str(deletion_request.verification_token)})
            )
            
            send_mail(
                'Verify Profile Data Deletion Request',
                f'Click the following link to delete your profile data: {verification_link}',
                'from@example.com',
                [email],
                fail_silently=False,
            )
        return render(request, 'users/delete_profile_data_submitted.html')

class VerifyProfileDataDeletionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        try:
            deletion_request = ProfileDataDeletionRequest.objects.get(verification_token=token, status='pending')
            if deletion_request.user:
                user = deletion_request.user
                user.first_name = "User"
                user.last_name = ""
                user.date_of_birth = None
                user.gender = None
                user.occupation = None
                user.country = None
                user.bio = None
                if user.profile_picture:
                    user.profile_picture.delete(save=False)
                user.save()
                
                deletion_request.status = 'completed'
                deletion_request.save()
                return render(request, 'users/delete_profile_data_confirmed.html')
            else:
                deletion_request.status = 'completed'
                deletion_request.save()
                return render(request, 'users/delete_profile_data_confirmed.html')
        except ProfileDataDeletionRequest.DoesNotExist:
            return standard_response(success=False, message="Invalid or expired verification link.", status_code=status.HTTP_400_BAD_REQUEST)


User = get_user_model()

@csrf_exempt
def account_deletion_request_view(request):
    return render(request, 'users/delete_account.html')
@method_decorator(csrf_exempt, name='dispatch')
class AccountDeletionAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return render(request, 'users/delete_account.html', {'error': 'Email is required.'})

        user = User.objects.filter(email=email).first()
        if user:
            deletion_request, created = AccountDeletionRequest.objects.get_or_create(user=user, defaults={'email': email})

            # Create a verification link
            verification_link = request.build_absolute_uri(
                reverse('users:verify_account_deletion', kwargs={'token': str(deletion_request.verification_token)})
            )

            # Send email to the user
            send_mail(
                'Verify Account Deletion Request',
                f'Click the following link to delete your account: {verification_link}',
                'from@example.com',  # Replace with your sending email
                [email],
                fail_silently=False,
            )
        return render(request, 'users/deletion_request_submitted.html')


class VerifyAccountDeletionView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        try:
            deletion_request = AccountDeletionRequest.objects.get(verification_token=token, status='pending')
            if deletion_request.user:
                deletion_request.user.delete()
                deletion_request.user = None
                deletion_request.status = 'completed'
                deletion_request.save()
                return render(request, 'users/deletion_confirmed.html')
            else:
                # Handle case where user is not found, but request exists
                deletion_request.status = 'completed'
                deletion_request.save()
                return render(request, 'users/deletion_confirmed.html')
        except AccountDeletionRequest.DoesNotExist:
            return standard_response(success=False, message="Invalid or expired verification link.", status_code=status.HTTP_400_BAD_REQUEST)



def standard_response(success=True, message="", data=None, errors=None, status_code=status.HTTP_200_OK):
    """
    Create standardized API response
    
    Args:
        success (bool): Whether operation was successful
        message (str): Response message
        data (dict): Response data
        errors (dict): Error details (for failed operations)
        status_code (int): HTTP status code
        
    Returns:
        Response: DRF Response object with standardized format
    """
    response_data = {
        'success': success,
        'message': message,
    }
    
    if data is not None:
        response_data['data'] = data
    
    if errors is not None:
        response_data['errors'] = errors
    
    return Response(response_data, status=status_code)


class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    """
    API endpoint for user registration (signup)
    
    POST /api/users/signup/
    
    Request body:
    {
        "name": "John Doe",
        "email": "john@example.com",
        "date_of_birth": "1990-01-15",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!"
    }
    """
    
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def post(self, request):
        """Handle user registration"""
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            return standard_response(
                success=True,
                message="Registration successful. Please check your email for the OTP to verify your account.",
                data={
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_email_verified': user.is_email_verified,
                    }
                },
                status_code=status.HTTP_201_CREATED
            )
        
        return standard_response(
            success=False,
            message="Registration failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class UserLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    """
    API endpoint for user login
    
    POST /api/users/login/
    
    Request body:
    {
        "email": "john@example.com",
        "password": "SecurePass123!"
    }
    """
    
    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer
    
    def post(self, request):
        """Handle user login"""
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Log login history
            UserLoginHistory.objects.create(
                user=user,
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

            # Track daily login in progress app
            #mark_user_login(user)
            
            # Return success response with tokens
            return standard_response(
                success=True,
                message="Login successful",
                data={
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'is_email_verified': user.is_email_verified,
                        'profile_picture': user.profile_picture.url if user.profile_picture else None, # noqa
                    },
                    'tokens': {
                        'access': access_token,
                        'refresh': refresh_token,
                    }
                },
                status_code=status.HTTP_200_OK
            )
        
        # Return validation errors
        return standard_response(
            success=False,
            message="Login failed",
            errors=serializer.errors,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    """
    API endpoint for user logout
    
    POST /api/users/logout/
    
    Request body:
    {
        "refresh": "refresh_token_here"
    }
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Handle user logout by blacklisting refresh token"""
        try:
            refresh_token = request.data.get('refresh')
            
            if not refresh_token:
                return standard_response(
                    success=False,
                    message="Refresh token is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return standard_response(
                success=True,
                message="Logout successful",
                status_code=status.HTTP_200_OK
            )
        
        except TokenError:
            return standard_response(
                success=False,
                message="Invalid or expired token",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return standard_response(
                success=False,
                message=f"Logout failed: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )


import logging

logger = logging.getLogger(__name__)

"""
API Views - Part 2: Email Verification, Password Management, Profile
"""


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    """
    API endpoint to verify OTP
    """
    permission_classes = [AllowAny]
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            try:
                user = User.objects.get(email=email)
                if user.otp == otp and user.is_otp_valid():
                    user.is_active = True
                    user.is_email_verified = True
                    user.clear_otp()
                    user.save()

                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)

                    return standard_response(
                        success=True,
                        message="OTP verified successfully. User logged in.",
                        data={
                            'user': {
                                'id': str(user.id),
                                'email': user.email,
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                'is_email_verified': user.is_email_verified,
                                'profile_picture': user.profile_picture.url if user.profile_picture else None,
                            },
                            'tokens': {
                                'access': access_token,
                                'refresh': refresh_token,
                            }
                        }
                    )
                else:
                    return standard_response(success=False, message="Invalid or expired OTP.", status_code=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return standard_response(success=False, message="User not found.", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, message="Invalid data.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    """
    API endpoint to resend OTP
    """
    permission_classes = [AllowAny]
    serializer_class = ResendOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    from .utils import generate_otp, send_otp_email
                    otp = generate_otp()
                    user.otp = otp
                    user.otp_created_at = timezone.now()
                    user.save(update_fields=['otp', 'otp_created_at'])
                    send_otp_email(user, otp)
                    return standard_response(success=True, message="OTP has been resent to your email.")
                else:
                    return standard_response(success=False, message="User is already active.", status_code=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return standard_response(success=False, message="User not found.", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, message="Invalid data.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    """
    API endpoint to request password reset
    
    POST /api/users/password-reset/
    
    Request body:
    {
        "email": "john@example.com"
    }
    """
    
    serializer_class = PasswordResetRequestSerializer
    
    def post(self, request):
        """Request password reset"""
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
            
            from users.models import User
            from business_account.models import BusinessAccount
            from .utils import generate_otp, send_otp_email
            
            # Try to find user in either model
            user = User.objects.filter(email=email).first()
            if not user:
                user = BusinessAccount.objects.filter(email=email).first()
            
            if user:
                # Generate and send OTP
                otp = generate_otp()
                user.otp = otp
                user.otp_created_at = timezone.now()
                user.save(update_fields=['otp', 'otp_created_at'])
                send_otp_email(user, otp)
            
            # Always return success message for security
            return standard_response(
                success=True,
                message="If an account with that email exists, an OTP has been sent.",
                status_code=status.HTTP_200_OK
            )
        
        return standard_response(
            success=False,
            message="Invalid request data",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PasswordResetOTPVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    """
    API endpoint to verify OTP for password reset
    """
    permission_classes = [AllowAny]
    serializer_class = PasswordResetOTPVerifySerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            try:
                user = User.objects.get(email=email)
                if user.otp == otp and user.is_otp_valid():
                    # OTP is correct, allow password reset
                    user.clear_otp()
                    return standard_response(success=True, message="OTP verified successfully. You can now reset your password.")
                else:
                    return standard_response(success=False, message="Invalid or expired OTP.", status_code=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return standard_response(success=False, message="User not found.", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, message="Invalid data.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    """
    API endpoint to confirm password reset with OTP
    
    POST /api/users/password-reset-confirm/
    
    Request body:
    {
        "email": "john@example.com",
        "password": "NewSecurePass123!",
        "confirm_password": "NewSecurePass123!"
    }
    """
    
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        """Confirm password reset"""
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['password']
            
            try:
                user = User.objects.get(email=email)
                
                # Set new password
                user.set_password(new_password)
                user.save()
                
                return standard_response(
                    success=True,
                    message="Password has been reset successfully. You can now login with your new password.",
                    status_code=status.HTTP_200_OK
                )
            
            except User.DoesNotExist:
                return standard_response(
                    success=False,
                    message="User not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
        
        return standard_response(
            success=False,
            message="Invalid request data",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    """
    API endpoint to change password (authenticated user)
    
    POST /api/users/password-change/
    
    Request body:
    {
        "old_password": "OldPass123!",
        "new_password": "NewSecurePass123!",
        "confirm_password": "NewSecurePass123!"
    }
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer
    
    def post(self, request):
        """Change password for authenticated user"""
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            
            # Verify old password
            if not user.check_password(old_password):
                return standard_response(
                    success=False,
                    message="Current password is incorrect",
                    errors={'old_password': ['Current password is incorrect']},
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            return standard_response(
                success=True,
                message="Password changed successfully",
                status_code=status.HTTP_200_OK
            )
        
        return standard_response(
            success=False,
            message="Invalid request data",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    """
    API endpoint to get and update user profile
    
    GET /api/users/profile/ - Get user profile
    PUT /api/users/profile/ - Update full profile
    PATCH /api/users/profile/ - Partial update profile
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get user profile"""
        user = request.user
        serializer = UserProfileSerializer(user)
        
        return standard_response(
            success=True,
            message="Profile retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request):
        """Update full user profile"""
        user = request.user
        serializer = UserProfileUpdateSerializer(user, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated profile
            profile_serializer = UserProfileSerializer(user)
            
            return standard_response(
                success=True,
                message="Profile updated successfully",
                data=profile_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return standard_response(
            success=False,
            message="Profile update failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def patch(self, request):
        """Partial update user profile"""
        user = request.user
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Return updated profile
            profile_serializer = UserProfileSerializer(user)
            
            return standard_response(
                success=True,
                message="Profile updated successfully",
                data=profile_serializer.data,
                status_code=status.HTTP_200_OK
            )
        
        return standard_response(
            success=False,
            message="Profile update failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class AccountDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    """
    API endpoint to delete user account
    
    DELETE /api/users/account-delete/
    
    Request body:
    {
        "password": "user_password",
        "confirm_deletion": true
    }
    """
    
    permission_classes = [IsAuthenticated]
    serializer_class = AccountDeleteSerializer
    
    def delete(self, request):
        """Delete user account"""
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            password = serializer.validated_data['password']
            
            # Verify password
            if not user.check_password(password):
                return standard_response(
                    success=False,
                    message="Incorrect password",
                    errors={'password': ['Incorrect password']},
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Store email for confirmation email
            user_email = user.email
            user_name = user.get_full_name()
            
            # Send account deletion confirmation email before deleting
            try:
                send_account_deletion_email(user)
            except Exception:
                pass  # Continue with deletion even if email fails
            
            # Delete user account
            user.delete()
            
            return standard_response(
                success=True,
                message="Account deleted successfully",
                status_code=status.HTTP_200_OK
            )
        
        return standard_response(
            success=False,
            message="Account deletion failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view with standard response format.
    Handles both standard User and BusinessAccount tokens.
    """
    serializer_class = MultiModelTokenRefreshSerializer
    
    def post(self, request, *args, **kwargs):
        """Refresh access token"""
        try:
            response = super().post(request, *args, **kwargs)
            
            return standard_response(
                success=True,
                message="Token refreshed successfully",
                data=response.data,
                status_code=status.HTTP_200_OK
            )
        
        except TokenError as e:
            return standard_response(
                success=False,
                message="Token refresh failed",
                errors={'detail': str(e)},
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            # Handle user not found during refresh logic in serializer
            if "User matching query does not exist" in str(e):
                return standard_response(
                    success=False,
                    message="User associated with this token no longer exists",
                    status_code=status.HTTP_401_UNAUTHORIZED
                )
            return standard_response(
                success=False,
                message="An unexpected error occurred during token refresh",
                errors={'detail': str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomTokenVerifyView(TokenVerifyView):
    """
    Custom token verify view with standard response format
    
    POST /api/users/token/verify/
    
    Request body:
    {
        "token": "access_token_here"
    }
    """
    
    def post(self, request, *args, **kwargs):
        """Verify access token"""
        try:
            response = super().post(request, *args, **kwargs)
            
            return standard_response(
                success=True,
                message="Token is valid",
                data={'valid': True},
                status_code=status.HTTP_200_OK
            )
        
        except TokenError as e:
            return standard_response(
                success=False,
                message="Token is invalid or expired",
                data={'valid': False},
                errors={'detail': str(e)},
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        except InvalidToken as e:
            return standard_response(
                success=False,
                message="Invalid token",
                data={'valid': False},
                errors={'detail': str(e)},
                status_code=status.HTTP_401_UNAUTHORIZED
            )

class SetLanguageView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LanguagePreferenceSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            language = serializer.validated_data['language']
            user = request.user
            user.preferred_language = language
            user.save(update_fields=['preferred_language'])
            return standard_response(success=True, message="Language preference updated successfully.", data={'language': language})
        return standard_response(success=False, message="Invalid request data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class UserProfileRegistrationView(generics.UpdateAPIView):
    serializer_class = UserProfileRegistrationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get_object(self):
        return self.request.user
