from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from .backends import BusinessAccountAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from django.utils import timezone
from django.contrib.auth import get_user_model # To access User model for example in CustomTokenRefreshView

from .models import BusinessAccount, VerificationRequest
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
    VerificationRequestSerializer,
    UserSimpleSerializer,
    PublicBusinessProfileSerializer,
)
from users.utils import (
    generate_otp,
    send_otp_email,
    send_welcome_email,
    get_client_ip,
    get_user_agent,
    get_full_media_url,
)

# Using the UserLoginHistory from users app for now, could create a BusinessAccountLoginHistory later
from users.models import UserLoginHistory, User
from .backends import MultiModelJWTAuthentication


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
            
            # Generate JWT tokens manually to avoid OutstandingToken crash
            # (SimpleJWT blacklist only supports AUTH_USER_MODEL)
            refresh = RefreshToken()
            refresh['user_id'] = str(business_account.id)
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
                    'account_type': 'business',
                    'business_account': {
                        'id': str(business_account.id),
                        'email': business_account.email,
                        'is_email_verified': business_account.is_email_verified,
                        'is_profile_complete': business_account.is_profile_complete,
                        'cover_photo': get_full_media_url(request, business_account.cover_photo),
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

                    # Generate JWT tokens manually to avoid OutstandingToken crash
                    # (SimpleJWT blacklist only supports AUTH_USER_MODEL)
                    refresh = RefreshToken()
                    refresh['user_id'] = str(business_account.id)
                    access_token = str(refresh.access_token)
                    refresh_token = str(refresh)

                    return standard_response(
                        success=True,
                        message="OTP verified successfully. Business account logged in.",
                        data={
                            'account_type': 'business',
                            'business_account': {
                                'id': str(business_account.id),
                                'email': business_account.email,
                                'is_email_verified': business_account.is_email_verified,
                                'is_profile_complete': business_account.is_profile_complete,
                                'cover_photo': get_full_media_url(request, business_account.cover_photo),
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
            email = serializer.validated_data['email'].lower()
            
            from users.models import User
            from .models import BusinessAccount
            from .utils import generate_otp, send_otp_email
            
            # Try to find user in either model
            user = BusinessAccount.objects.filter(email=email).first()
            if not user:
                user = User.objects.filter(email=email).first()
            
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
    serializer_class = PasswordResetOTPVerifySerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
            otp = serializer.validated_data['otp']
            
            from users.models import User
            from .models import BusinessAccount
            
            # Try to find user in either model
            user = BusinessAccount.objects.filter(email=email).first()
            if not user:
                user = User.objects.filter(email=email).first()
                
            if user:
                if user.otp == otp and user.is_otp_valid():
                    user.clear_otp()
                    return standard_response(success=True, message="OTP verified successfully. You can now reset your password.")
                else:
                    return standard_response(success=False, message="Invalid or expired OTP.", status_code=status.HTTP_400_BAD_REQUEST)
            
            return standard_response(success=False, message="User not found.", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, message="Invalid data.", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
            new_password = serializer.validated_data['password']
            
            from users.models import User
            from .models import BusinessAccount
            
            # Try to find user in either model
            user = BusinessAccount.objects.filter(email=email).first()
            if not user:
                user = User.objects.filter(email=email).first()
                
            if user:
                user.set_password(new_password)
                user.save()
                
                return standard_response(
                    success=True,
                    message="Password has been reset successfully. You can now login with your new password.",
                    status_code=status.HTTP_200_OK
                )
            
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
    authentication_classes = [BusinessAccountAuthentication] # Explicitly set authentication
    serializer_class = PasswordChangeSerializer
    
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        if serializer.is_valid():
            business_account = request.user # request.user is how DRF passes the authenticated user/account
            # Ensure the authenticated user is a BusinessAccount instance
            if not isinstance(business_account, BusinessAccount):
                return standard_response(success=False, message="Unauthorized access.", status_code=status.HTTP_403_FORBIDDEN)


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


class BusinessAccountProfileRegistrationView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [BusinessAccountAuthentication] # Explicitly set authentication
    serializer_class = BusinessAccountProfileRegistrationSerializer

    def get_object(self):
        # Assuming request.user will be a BusinessAccount instance if authenticated via JWT
        business_account = self.request.user
        if not isinstance(business_account, BusinessAccount):
            raise InvalidToken("Invalid token for Business Account.") # Or a custom exception
        return business_account

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        if serializer.is_valid():
            self.perform_update(serializer)
            return standard_response(
                success=True,
                message="Business profile registration completed successfully",
                data=serializer.data,
                status_code=status.HTTP_200_OK
            )
        return standard_response(
            success=False,
            message="Profile registration failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    def perform_update(self, serializer):
        business_account = serializer.save()
        if not business_account.is_profile_complete:
            business_account.is_profile_complete = True
            business_account.save(update_fields=['is_profile_complete'])


class BusinessAccountProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [BusinessAccountAuthentication] # Explicitly set authentication
    serializer_class = BusinessAccountProfileSerializer

    def get(self, request):
        business_account = request.user
        if not isinstance(business_account, BusinessAccount):
            return standard_response(success=False, message="Unauthorized access.", status_code=status.HTTP_403_FORBIDDEN)
        
        serializer = self.serializer_class(business_account, context={'request': request})
        return standard_response(
            success=True,
            message="Business account profile retrieved successfully",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )

    def put(self, request):
        business_account = request.user
        if not isinstance(business_account, BusinessAccount):
            return standard_response(success=False, message="Unauthorized access.", status_code=status.HTTP_403_FORBIDDEN)
        
        serializer = self.serializer_class(business_account, data=request.data, context={'request': request})
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
        if not isinstance(business_account, BusinessAccount):
            return standard_response(success=False, message="Unauthorized access.", status_code=status.HTTP_403_FORBIDDEN)
        
        serializer = self.serializer_class(business_account, data=request.data, partial=True, context={'request': request})
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


class BusinessAccountLogoutView(APIView):
    """
    API endpoint for business account logout
    
    POST /api/business/logout/
    
    Request body:
    {
        "refresh": "refresh_token_here"
    }
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [BusinessAccountAuthentication]
    
    def post(self, request):
        """Handle business account logout by blacklisting refresh token"""
        try:
            refresh_token = request.data.get('refresh')
            
            if not refresh_token:
                return standard_response(
                    success=False,
                    message="Refresh token is required",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            # Blacklist only works for AUTH_USER_MODEL (User)
            # BusinessAccount tokens are not tracked in the OutstandingToken table
            # However, we still return success to indicate local logout is complete
            if isinstance(request.user, User):
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except (TokenError, AttributeError):
                    pass
            
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


class VerificationRequestCreateView(APIView):
    """
    Standard user requests verification from a business account
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]
    serializer_class = VerificationRequestSerializer

    def post(self, request):
        if not isinstance(request.user, User):
            return standard_response(
                success=False, 
                message="Only standard users can request verification.", 
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        business_id = request.data.get('business_account')
        if not business_id:
            return standard_response(
                success=False, 
                message="Business account ID is required.", 
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            business = BusinessAccount.objects.get(id=business_id)
        except BusinessAccount.DoesNotExist:
            return standard_response(
                success=False, 
                message="Business account not found.", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        if VerificationRequest.objects.filter(user=request.user, business_account=business).exists():
            return standard_response(
                success=False, 
                message="Verification request already sent to this business.", 
                status_code=status.HTTP_400_BAD_REQUEST
            )

        verification_request = VerificationRequest.objects.create(
            user=request.user,
            business_account=business,
            status='pending'
        )
        
        serializer = self.serializer_class(verification_request)
        return standard_response(
            success=True,
            message="Verification request sent successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class VerificationRequestListView(APIView):
    """
    Business account sees list of verification requests received
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [BusinessAccountAuthentication]
    serializer_class = VerificationRequestSerializer

    def get(self, request):
        if not isinstance(request.user, BusinessAccount):
             return standard_response(
                 success=False, 
                 message="Only business accounts can access this.", 
                 status_code=status.HTTP_403_FORBIDDEN
             )
        
        requests = VerificationRequest.objects.filter(business_account=request.user, status='pending')
        serializer = self.serializer_class(requests, many=True)
        return standard_response(
            success=True,
            message="Verification requests retrieved successfully.",
            data=serializer.data
        )


class VerificationRequestActionView(APIView):
    """
    Business account accepts or rejects a verification request
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [BusinessAccountAuthentication]

    def post(self, request, pk):
        if not isinstance(request.user, BusinessAccount):
             return standard_response(
                 success=False, 
                 message="Only business accounts can access this.", 
                 status_code=status.HTTP_403_FORBIDDEN
             )
        
        try:
            verification_request = VerificationRequest.objects.get(id=pk, business_account=request.user)
        except VerificationRequest.DoesNotExist:
            return standard_response(
                success=False, 
                message="Verification request not found.", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        action = request.data.get('action') # 'accept' or 'reject'
        if action == 'accept':
            verification_request.status = 'accepted'
            verification_request.save()
            
            # Update user's is_verified status
            user = verification_request.user
            user.is_verified = True
            user.save(update_fields=['is_verified'])
            
            return standard_response(success=True, message="Verification request accepted. User is now verified.")
        elif action == 'reject':
            verification_request.status = 'rejected'
            verification_request.save()
            return standard_response(success=True, message="Verification request rejected.")
        else:
            return standard_response(
                success=False, 
                message="Invalid action. Use 'accept' or 'reject'.", 
                status_code=status.HTTP_400_BAD_REQUEST
            )


class BusinessMemberListView(APIView):
    """
    Business account sees list of users they have verified
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [BusinessAccountAuthentication]
    serializer_class = UserSimpleSerializer

    def get(self, request):
        if not isinstance(request.user, BusinessAccount):
             return standard_response(
                 success=False, 
                 message="Only business accounts can access this.", 
                 status_code=status.HTTP_403_FORBIDDEN
             )
        
        # Members are users who have an accepted verification request with this business
        memberships = VerificationRequest.objects.filter(business_account=request.user, status='accepted')
        users = [membership.user for membership in memberships]
        serializer = self.serializer_class(users, many=True)
        return standard_response(
            success=True,
            message="Member list retrieved successfully.",
            data=serializer.data
        )


class RemoveMemberView(APIView):
    """
    Business account removes a user from their verified member list
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [BusinessAccountAuthentication]

    def post(self, request, user_id):
        if not isinstance(request.user, BusinessAccount):
             return standard_response(
                 success=False, 
                 message="Only business accounts can access this.", 
                 status_code=status.HTTP_403_FORBIDDEN
             )
        
        try:
            membership = VerificationRequest.objects.get(
                business_account=request.user, 
                user_id=user_id, 
                status='accepted'
            )
        except VerificationRequest.DoesNotExist:
            return standard_response(
                success=False, 
                message="Member not found.", 
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # Delete the membership
        membership.delete()
        
        # Check if user is still verified by any OTHER business.
        # If not, set user.is_verified = False.
        user = User.objects.get(id=user_id)
        if not VerificationRequest.objects.filter(user=user, status='accepted').exists():
            user.is_verified = False
            user.save(update_fields=['is_verified'])

        return standard_response(success=True, message="Member removed successfully.")


class OtherBusinessProfileView(APIView):
    """
    View a business's public profile by their ID.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def get(self, request, pk):
        try:
            business = BusinessAccount.objects.get(pk=pk)
            serializer = PublicBusinessProfileSerializer(business, context={'request': request})
            return standard_response(
                success=True,
                message="Business profile retrieved successfully",
                data=serializer.data
            )
        except BusinessAccount.DoesNotExist:
            return standard_response(
                success=False,
                message="Business not found",
                status_code=status.HTTP_404_NOT_FOUND
            )
