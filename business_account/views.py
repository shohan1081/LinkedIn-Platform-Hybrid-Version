from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken, AuthenticationFailed
from .backends import BusinessAccountAuthentication
from django.utils import timezone
from django.contrib.auth import get_user_model # To access User model for example in CustomTokenRefreshView
from django.http import Http404 # Import Http404

from .models import BusinessAccount
from .serializers import (
    BusinessAccountRegistrationSerializer,
    BusinessAccountLoginSerializer,
    VerifyOTPSerializer,
    ResendOTPSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordChangeSerializer,
    BusinessAccountProfileRegistrationSerializer,
    BusinessAccountProfileSerializer,
    PasswordResetOTPVerifySerializer,
)
from .utils import (
    generate_otp,
    send_otp_email,
    send_welcome_email,
    get_client_ip,
    get_user_agent,
)

# Using the UserLoginHistory from users app for now, could create a BusinessAccountLoginHistory later
from users.models import UserLoginHistory


def standard_response(success=True, message="", data=None, errors=None, status_code=status.HTTP_200_OK):
    """
    Create standardized API response
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


class BusinessAccountRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = BusinessAccountRegistrationSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            business_account = serializer.save()
            
            # Send welcome email (optional)
            send_welcome_email(business_account)

            return standard_response(
                success=True,
                message="Registration successful. Please check your email for the OTP to verify your account.",
                data={
                    'business_account': {
                        'id': str(business_account.id),
                        'email': business_account.email,
                        'is_email_verified': business_account.is_email_verified,
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


class BusinessAccountLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = BusinessAccountLoginSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            business_account = serializer.validated_data['business_account']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(business_account)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Update last login
            business_account.last_login = timezone.now()
            business_account.save(update_fields=['last_login'])
            
            # Log login history (using UserLoginHistory for simplicity, could create BusinessAccountLoginHistory)
            # This would require a ForeignKey to BusinessAccount in UserLoginHistory
            # For now, it will not log. Uncomment and adapt if a specific BusinessAccountLoginHistory is created.
            # UserLoginHistory.objects.create(
            #     user=business_account, # This would require user to be a BusinessAccount or a generic foreign key
            #     ip_address=get_client_ip(request),
            #     user_agent=get_user_agent(request),
            # )
            
            return standard_response(
                success=True,
                message="Login successful",
                data={
                    'business_account': {
                        'id': str(business_account.id),
                        'email': business_account.email,
                        'is_email_verified': business_account.is_email_verified,
                    },
                    'tokens': {
                        'access': access_token,
                        'refresh': refresh_token,
                    }
                },
                status_code=status.HTTP_200_OK
            )
        
        return standard_response(
            success=False,
            message="Login failed",
            errors=serializer.errors,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = VerifyOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            try:
                business_account = BusinessAccount.objects.get(email=email)
                if business_account.otp == otp and business_account.is_otp_valid():
                    business_account.is_active = True
                    business_account.is_email_verified = True
                    business_account.clear_otp()
                    business_account.save()

                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(business_account)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)

                    return standard_response(
                        success=True,
                        message="OTP verified successfully. Business account logged in.",
                        data={
                            'business_account': {
                                'id': str(business_account.id),
                                'email': business_account.email,
                                'is_email_verified': business_account.is_email_verified,
                            },
                            'tokens': {
                                'access': access_token,
                                'refresh': refresh_token,
                            }
                        }
                    )
                else:
                    return standard_response(success=False, message="Invalid or expired OTP.", status_code=status.HTTP_400_BAD_REQUEST)
            except BusinessAccount.DoesNotExist:
                return standard_response(success=False, message="Business account not found.", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, message="Invalid data.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ResendOTPSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                business_account = BusinessAccount.objects.get(email=email)
                if not business_account.is_active:
                    otp = generate_otp()
                    business_account.otp = otp
                    business_account.otp_created_at = timezone.now()
                    business_account.save(update_fields=['otp', 'otp_created_at'])
                    send_otp_email(business_account, otp)
                    return standard_response(success=True, message="OTP has been resent to your email.")
                else:
                    return standard_response(success=False, message="Business account is already active.", status_code=status.HTTP_400_BAD_REQUEST)
            except BusinessAccount.DoesNotExist:
                return standard_response(success=False, message="Business account not found.", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, message="Invalid data.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetRequestSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                business_account = BusinessAccount.objects.get(email=email)
                
                otp = generate_otp()
                business_account.otp = otp
                business_account.otp_created_at = timezone.now()
                business_account.save(update_fields=['otp', 'otp_created_at'])
                send_otp_email(business_account, otp)
            
            except BusinessAccount.DoesNotExist:
                pass # For security, don't reveal if email exists or not
            
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
    serializer_class = PasswordResetOTPVerifySerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            try:
                business_account = BusinessAccount.objects.get(email=email)
                if business_account.otp == otp and business_account.is_otp_valid():
                    business_account.clear_otp()
                    return standard_response(success=True, message="OTP verified successfully. You can now reset your password.")
                else:
                    return standard_response(success=False, message="Invalid or expired OTP.", status_code=status.HTTP_400_BAD_REQUEST)
            except BusinessAccount.DoesNotExist:
                return standard_response(success=False, message="Business account not found.", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, message="Invalid data.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['password']
            
            try:
                business_account = BusinessAccount.objects.get(email=email)
                
                business_account.set_password(new_password)
                business_account.save()
                
                return standard_response(
                    success=True,
                    message="Password has been reset successfully. You can now login with your new password.",
                    status_code=status.HTTP_200_OK
                )
            
            except BusinessAccount.DoesNotExist:
                return standard_response(
                    success=False,
                    message="Business account not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
        
        return standard_response(
            success=False,
            message="Invalid request data",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class PasswordChangeView(APIView):
    serializer_class = PasswordChangeSerializer
    authentication_classes = [BusinessAccountAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            business_account = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            
            if not business_account.check_password(old_password):
                return standard_response(
                    success=False,
                    message="Current password is incorrect",
                    errors={'old_password': ['Current password is incorrect']},
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            business_account.set_password(new_password)
            business_account.save()
            
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


from rest_framework.exceptions import AuthenticationFailed
# ... other imports ...

class BusinessAccountProfileRegistrationView(generics.UpdateAPIView):
    serializer_class = BusinessAccountProfileRegistrationSerializer
    authentication_classes = [BusinessAccountAuthentication]
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        business_account = serializer.save()
        if not business_account.is_profile_complete:
            business_account.is_profile_complete = True
            business_account.save(update_fields=['is_profile_complete'])


from .backends import BusinessAccountAuthentication
from rest_framework.permissions import IsAuthenticated

class BusinessAccountProfileView(APIView):
    authentication_classes = [BusinessAccountAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = BusinessAccountProfileSerializer

    def get(self, request):
        business_account = request.user
        
        serializer = self.serializer_class(business_account)
        return standard_response(
            success=True,
            message="Business account profile retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def put(self, request):
        business_account = request.user
        
        serializer = self.serializer_class(business_account, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return standard_response(
                success=True,
                message="Business account profile updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        return standard_response(
            success=False,
            message="Profile update failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def patch(self, request):
        business_account = request.user
        
        serializer = self.serializer_class(business_account, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return standard_response(
                success=True,
                message="Business account profile updated successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        return standard_response(
            success=False,
            message="Profile update failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )





class CustomBusinessTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self, request, *args, **kwargs):
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
        except InvalidToken as e:
            return standard_response(
                success=False,
                message="Invalid token",
                errors={'detail': str(e)},
                status_code=status.HTTP_401_UNAUTHORIZED
            )


class CustomBusinessTokenVerifyView(TokenVerifyView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
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