from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Q as DjangoQ
from django.contrib.contenttypes.models import ContentType

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from business_account.backends import MultiModelJWTAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

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
    EducationSerializer,
    ExperienceSerializer,
    SupportTicketSerializer,
    RecommendationSerializer,
    GiveRecommendationSerializer,
    PublicUserProfileSerializer,
    FollowAccountSerializer,
    FollowToggleSerializer,
)
from .utils import (
    send_welcome_email,
    send_account_deletion_email,
    get_client_ip,
    get_user_agent,
    get_full_media_url,
)
from .models import (
    UserLoginHistory, 
    AccountDeletionRequest, 
    ProfileDataDeletionRequest, 
    Education, 
    Experience, 
    Recommendation,
    Follow
)

User = get_user_model()

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

class RecommendationListView(APIView):
    """
    List recommendations for a specific user or business.
    Query params:
    - id: UUID of the receiver
    - type: 'user' or 'business'
    """
    permission_classes = [AllowAny]
    authentication_classes = [MultiModelJWTAuthentication]

    def get(self, request):
        receiver_id = request.query_params.get('id')
        receiver_type = request.query_params.get('type')

        if not receiver_id or not receiver_type:
            return standard_response(
                success=False,
                message="Both 'id' and 'type' (user/business) query parameters are required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        from business_account.models import BusinessAccount
        model = User if receiver_type == 'user' else BusinessAccount
        try:
            receiver_ct = ContentType.objects.get_for_model(model)
            recommendations = Recommendation.objects.filter(
                receiver_content_type=receiver_ct,
                receiver_object_id=receiver_id
            )
            serializer = RecommendationSerializer(recommendations, many=True, context={'request': request})
            return standard_response(
                success=True,
                message="Recommendations retrieved successfully",
                data=serializer.data
            )
        except Exception as e:
            return standard_response(
                success=False,
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

class GiveRecommendationView(APIView):
    """
    Give or update a recommendation for another user/business.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def post(self, request):
        serializer = GiveRecommendationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return standard_response(
                success=True,
                message="Recommendation submitted successfully"
            )
        return standard_response(
            success=False,
            message="Failed to submit recommendation",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )

class GlobalUserSearchView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        query = request.query_params.get('q', '')
        if not query:
            return standard_response(success=True, data={'users': [], 'businesses': []})

        users = User.objects.filter(
            DjangoQ(first_name__icontains=query) | 
            DjangoQ(last_name__icontains=query) | 
            DjangoQ(email__icontains=query)
        ).filter(is_active=True)[:10]

        from business_account.models import BusinessAccount
        businesses = BusinessAccount.objects.filter(
            DjangoQ(business_name__icontains=query) | 
            DjangoQ(email__icontains=query)
        ).filter(is_active=True)[:10]

        user_results = []
        for u in users:
            user_results.append({
                'id': str(u.id),
                'name': f"{u.first_name} {u.last_name}".strip() or u.email,
                'type': 'user',
                'profile_picture': get_full_media_url(request, u.profile_picture)
            })

        business_results = []
        for b in businesses:
            business_results.append({
                'id': str(b.id),
                'name': b.business_name or b.email,
                'type': 'business',
                'profile_picture': get_full_media_url(request, b.profile_picture)
            })

        return standard_response(
            success=True,
            message="Search results retrieved",
            data={'users': user_results, 'businesses': business_results}
        )

class SupportTicketView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = SupportTicketSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email_address = serializer.validated_data['email_address']
            subject = serializer.validated_data['subject']
            message = serializer.validated_data['message']
            admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'admin@example.com')
            email_subject = f"Support Request: {subject}"
            email_message = f"From: {email_address}\n\nMessage:\n{message}"
            try:
                send_mail(email_subject, email_message, settings.DEFAULT_FROM_EMAIL, [admin_email], fail_silently=False)
                return standard_response(success=True, message="Support request sent successfully.")
            except Exception as e:
                return standard_response(success=False, message=f"Failed: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return standard_response(success=False, message="Invalid data", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class IsRegularUser(IsAuthenticated):
    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        if not is_authenticated: return False
        return isinstance(request.user, User)

class EducationListCreateView(APIView):
    permission_classes = [IsRegularUser]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        educations = Education.objects.filter(user=request.user)
        serializer = EducationSerializer(educations, many=True)
        return standard_response(success=True, message="Educations retrieved", data=serializer.data)
    def post(self, request):
        serializer = EducationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return standard_response(success=True, message="Education added", data=serializer.data, status_code=status.HTTP_201_CREATED)
        return standard_response(success=False, message="Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class EducationDetailView(APIView):
    permission_classes = [IsRegularUser]
    authentication_classes = [JWTAuthentication]
    def get_object(self, pk, user):
        try: return Education.objects.get(pk=pk, user=user)
        except Education.DoesNotExist: return None
    def get(self, request, pk):
        edu = self.get_object(pk, request.user)
        if not edu: return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=True, data=EducationSerializer(edu).data)
    def put(self, request, pk):
        edu = self.get_object(pk, request.user)
        if not edu: return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        serializer = EducationSerializer(edu, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return standard_response(success=True, message="Updated", data=serializer.data)
        return standard_response(success=False, message="Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, pk):
        edu = self.get_object(pk, request.user)
        if not edu: return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        edu.delete()
        return standard_response(success=True, message="Deleted")

class ExperienceListCreateView(APIView):
    permission_classes = [IsRegularUser]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        exp = Experience.objects.filter(user=request.user)
        return standard_response(success=True, data=ExperienceSerializer(exp, many=True).data)
    def post(self, request):
        serializer = ExperienceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return standard_response(success=True, message="Added", data=serializer.data, status_code=status.HTTP_201_CREATED)
        return standard_response(success=False, message="Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class ExperienceDetailView(APIView):
    permission_classes = [IsRegularUser]
    authentication_classes = [JWTAuthentication]
    def get_object(self, pk, user):
        try: return Experience.objects.get(pk=pk, user=user)
        except Experience.DoesNotExist: return None
    def get(self, request, pk):
        exp = self.get_object(pk, request.user)
        if not exp: return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=True, data=ExperienceSerializer(exp).data)
    def put(self, request, pk):
        exp = self.get_object(pk, request.user)
        if not exp: return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        serializer = ExperienceSerializer(exp, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return standard_response(success=True, message="Updated", data=serializer.data)
        return standard_response(success=False, message="Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
    def delete(self, request, pk):
        exp = self.get_object(pk, request.user)
        if not exp: return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        exp.delete()
        return standard_response(success=True, message="Deleted")

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = UserRegistrationSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return standard_response(success=True, message="OTP sent.", data={'user': {'id': str(user.id), 'email': user.email}}, status_code=status.HTTP_201_CREATED)
        return standard_response(success=False, message="Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = UserLoginSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            UserLoginHistory.objects.create(user=user, ip_address=get_client_ip(request), user_agent=get_user_agent(request))
            return standard_response(success=True, message="Login successful", data={
                'account_type': 'personal',
                'user': {'id': str(user.id), 'email': user.email, 'is_profile_complete': user.is_profile_complete, 'profile_picture': get_full_media_url(request, user.profile_picture)},
                'tokens': {'access': str(refresh.access_token), 'refresh': str(refresh)}
            })
        return standard_response(success=False, message="Login failed", errors=serializer.errors, status_code=status.HTTP_401_UNAUTHORIZED)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return standard_response(success=True, data=serializer.data)
    def patch(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return standard_response(success=True, message="Profile updated", data=UserProfileSerializer(request.user, context={'request': request}).data)
        return standard_response(success=False, message="Failed", errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)
    def put(self, request):
        return self.patch(request)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = VerifyOTPSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email, otp = serializer.validated_data['email'], serializer.validated_data['otp']
            try:
                user = User.objects.get(email=email)
                if user.otp == otp and user.is_otp_valid():
                    user.is_active = True
                    user.is_email_verified = True
                    user.clear_otp()
                    user.save()
                    refresh = RefreshToken.for_user(user)
                    return standard_response(success=True, message="OTP verified", data={
                        'account_type': 'personal',
                        'user': {'id': str(user.id), 'email': user.email, 'profile_picture': get_full_media_url(request, user.profile_picture)},
                        'tokens': {'access': str(refresh.access_token), 'refresh': str(refresh)}
                    })
                return standard_response(success=False, message="Invalid OTP", status_code=status.HTTP_400_BAD_REQUEST)
            except User.DoesNotExist: return standard_response(success=False, message="User not found", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ResendOTPSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(email=serializer.validated_data['email'])
                from .utils import generate_otp, send_otp_email
                otp = generate_otp()
                user.otp, user.otp_created_at = otp, timezone.now()
                user.save()
                send_otp_email(user, otp)
                return standard_response(success=True, message="OTP resent.")
            except User.DoesNotExist: return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetRequestSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower()
            from business_account.models import BusinessAccount
            user = User.objects.filter(email=email).first() or BusinessAccount.objects.filter(email=email).first()
            if user:
                from .utils import generate_otp, send_otp_email
                otp = generate_otp()
                user.otp, user.otp_created_at = otp, timezone.now()
                user.save()
                send_otp_email(user, otp)
            return standard_response(success=True, message="If email exists, OTP sent.")
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class PasswordResetOTPVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetOTPVerifySerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email, otp = serializer.validated_data['email'].lower(), serializer.validated_data['otp']
            from business_account.models import BusinessAccount
            user = User.objects.filter(email=email).first() or BusinessAccount.objects.filter(email=email).first()
            if user and user.otp == otp and user.is_otp_valid():
                user.clear_otp()
                return standard_response(success=True, message="OTP verified.")
            return standard_response(success=False, message="Invalid OTP", status_code=status.HTTP_400_BAD_REQUEST)
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = PasswordResetConfirmSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email, pwd = serializer.validated_data['email'].lower(), serializer.validated_data['password']
            from business_account.models import BusinessAccount
            user = User.objects.filter(email=email).first() or BusinessAccount.objects.filter(email=email).first()
            if user:
                user.set_password(pwd)
                user.save()
                return standard_response(success=True, message="Password reset success.")
            return standard_response(success=False, message="Not found", status_code=status.HTTP_404_NOT_FOUND)
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = PasswordChangeSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            if not request.user.check_password(serializer.validated_data['old_password']):
                return standard_response(success=False, message="Old password wrong", status_code=status.HTTP_400_BAD_REQUEST)
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return standard_response(success=True, message="Changed.")
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class AccountDeleteView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    serializer_class = AccountDeleteSerializer
    def delete(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            if not request.user.check_password(serializer.validated_data['password']):
                return standard_response(success=False, message="Wrong password", status_code=status.HTTP_400_BAD_REQUEST)
            send_account_deletion_email(request.user)
            request.user.delete()
            return standard_response(success=True, message="Deleted.")
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = MultiModelTokenRefreshSerializer
    def post(self, request, *args, **kwargs):
        try: return standard_response(success=True, data=super().post(request, *args, **kwargs).data)
        except Exception as e: return standard_response(success=False, message=str(e), status_code=status.HTTP_401_UNAUTHORIZED)

class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        try: return standard_response(success=True, data={'valid': True})
        except Exception as e: return standard_response(success=False, message=str(e), status_code=status.HTTP_401_UNAUTHORIZED)

class SetLanguageView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        lang = request.data.get('language')
        if lang in ['en', 'hi', 'pt']:
            request.user.preferred_language = lang
            request.user.save()
            return standard_response(success=True, message="Language set.")
        return standard_response(success=False, message="Invalid lang", status_code=status.HTTP_400_BAD_REQUEST)

class UserProfileRegistrationView(generics.UpdateAPIView):
    serializer_class = UserProfileRegistrationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]
    def get_object(self): return self.request.user
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        if serializer.is_valid():
            user = serializer.save()
            user.is_profile_complete = True
            user.save()
            return standard_response(success=True, message="Registered", data=serializer.data)
        return standard_response(success=False, errors=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def delete_profile_data_request_view(request): return render(request, 'users/delete_profile_data_request.html')

class ProfileDataDeletionAPIView(APIView):
    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            req, _ = ProfileDataDeletionRequest.objects.get_or_create(user=user, email=email)
            link = request.build_absolute_uri(reverse('users:verify_profile_data_deletion', kwargs={'token': str(req.verification_token)}))
            send_mail('Verify Deletion', f'Link: {link}', 'from@example.com', [email])
        return render(request, 'users/delete_profile_data_submitted.html')

class VerifyProfileDataDeletionView(APIView):
    def get(self, request, token):
        try:
            req = ProfileDataDeletionRequest.objects.get(verification_token=token, status='pending')
            if req.user:
                u = req.user
                u.first_name, u.last_name, u.about = "User", "", None
                u.save()
            req.status = 'completed'; req.save()
            return render(request, 'users/delete_profile_data_confirmed.html')
        except: return standard_response(success=False, message="Invalid link", status_code=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def account_deletion_request_view(request): return render(request, 'users/delete_account.html')

class AccountDeletionAPIView(APIView):
    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            req, _ = AccountDeletionRequest.objects.get_or_create(user=user, email=email)
            link = request.build_absolute_uri(reverse('users:verify_account_deletion', kwargs={'token': str(req.verification_token)}))
            send_mail('Verify Deletion', f'Link: {link}', 'from@example.com', [email])
        return render(request, 'users/deletion_request_submitted.html')

class VerifyAccountDeletionView(APIView):
    def get(self, request, token):
        try:
            req = AccountDeletionRequest.objects.get(verification_token=token, status='pending')
            if req.user: req.user.delete()
            req.status = 'completed'; req.save()
            return render(request, 'users/deletion_confirmed.html')
        except: return standard_response(success=False, message="Invalid link", status_code=status.HTTP_400_BAD_REQUEST)

class OtherUserProfileView(APIView):
    """
    View another user's public profile by their ID (supports both regular and business accounts).
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def get(self, request, pk):
        from business_account.models import BusinessAccount
        from business_account.serializers import PublicBusinessProfileSerializer

        # Try to find a regular user first
        try:
            user = User.objects.get(pk=pk)
            serializer = PublicUserProfileSerializer(user, context={'request': request})
            return standard_response(
                success=True,
                message="User profile retrieved successfully",
                data={**serializer.data, 'account_type': 'personal'}
            )
        except User.DoesNotExist:
            # If not found, try to find a business account
            try:
                business = BusinessAccount.objects.get(pk=pk)
                serializer = PublicBusinessProfileSerializer(business, context={'request': request})
                return standard_response(
                    success=True,
                    message="Business profile retrieved successfully",
                    data={**serializer.data, 'account_type': 'business'}
                )
            except BusinessAccount.DoesNotExist:
                return standard_response(
                    success=False,
                    message="Account not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )

class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
            return standard_response(success=True, message="Logged out")
        except: return standard_response(success=True, message="Logged out")

class FollowToggleView(APIView):
    """
    API endpoint to follow or unfollow another user/business.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def post(self, request):
        serializer = FollowToggleSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        follower = request.user
        followed = serializer.validated_data['followed_instance']
        
        follower_ct = ContentType.objects.get_for_model(follower)
        followed_ct = ContentType.objects.get_for_model(followed)

        follow_qs = Follow.objects.filter(
            follower_content_type=follower_ct,
            follower_object_id=follower.id,
            followed_content_type=followed_ct,
            followed_object_id=followed.id
        )

        if follow_qs.exists():
            follow_qs.delete()
            return standard_response(success=True, message=f"You have unfollowed {followed}")
        else:
            Follow.objects.create(
                follower_content_type=follower_ct,
                follower_object_id=follower.id,
                followed_content_type=followed_ct,
                followed_object_id=followed.id
            )
            return standard_response(success=True, message=f"You are now following {followed}")

class FollowersListView(APIView):
    """
    API endpoint to list all followers of a specific user/business.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def get(self, request, pk):
        from business_account.models import BusinessAccount
        
        # Determine the target account
        target = None
        try:
            target = User.objects.get(pk=pk)
        except User.DoesNotExist:
            try:
                target = BusinessAccount.objects.get(pk=pk)
            except BusinessAccount.DoesNotExist:
                return standard_response(success=False, message="Account not found", status_code=status.HTTP_404_NOT_FOUND)

        target_ct = ContentType.objects.get_for_model(target)
        follows = Follow.objects.filter(followed_content_type=target_ct, followed_object_id=target.id)
        
        followers = [f.follower for f in follows]
        serializer = FollowAccountSerializer(followers, many=True, context={'request': request})
        
        return standard_response(
            success=True,
            message="Followers retrieved successfully",
            data=serializer.data
        )

class FollowingListView(APIView):
    """
    API endpoint to list all accounts followed by a specific user/business.
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def get(self, request, pk):
        from business_account.models import BusinessAccount
        
        # Determine the target account
        target = None
        try:
            target = User.objects.get(pk=pk)
        except User.DoesNotExist:
            try:
                target = BusinessAccount.objects.get(pk=pk)
            except BusinessAccount.DoesNotExist:
                return standard_response(success=False, message="Account not found", status_code=status.HTTP_404_NOT_FOUND)

        target_ct = ContentType.objects.get_for_model(target)
        follows = Follow.objects.filter(follower_content_type=target_ct, follower_object_id=target.id)
        
        followed_accounts = [f.followed for f in follows]
        serializer = FollowAccountSerializer(followed_accounts, many=True, context={'request': request})
        
        return standard_response(
            success=True,
            message="Following list retrieved successfully",
            data=serializer.data
        )
