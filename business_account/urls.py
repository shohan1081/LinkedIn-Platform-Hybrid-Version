from django.urls import path
from .views import (
    BusinessAccountRegistrationView,
    BusinessAccountLoginView,
    VerifyOTPView,
    ResendOTPView,
    BusinessAccountLogoutView,
    PasswordResetRequestView,
    PasswordResetOTPVerifyView,
    PasswordResetConfirmView,
    PasswordChangeView,
    BusinessAccountProfileRegistrationView,
    BusinessAccountProfileView,
    CustomBusinessTokenRefreshView,
    CustomBusinessTokenVerifyView,
    VerificationRequestCreateView,
    VerificationRequestListView,
    VerificationRequestActionView,
    BusinessMemberListView,
    RemoveMemberView,
    OtherBusinessProfileView,
)
from users.views import RecommendationListView, GiveRecommendationView

app_name = 'business_account'

urlpatterns = [
    # Authentication endpoints
    path('signup/', BusinessAccountRegistrationView.as_view(), name='signup'),
    path('login/', BusinessAccountLoginView.as_view(), name='login'),
    path('logout/', BusinessAccountLogoutView.as_view(), name='logout'),
    
    # Token management
    path('token/refresh/', CustomBusinessTokenRefreshView.as_view(), name='token-refresh'),
    path('token/verify/', CustomBusinessTokenVerifyView.as_view(), name='token-verify'),
    
    # OTP verification
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    
    # Password management
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-otp-verify/', PasswordResetOTPVerifyView.as_view(), name='password-reset-otp-verify'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password-change/', PasswordChangeView.as_view(), name='password-change'),
    
    # Profile management
    path('profile-register/', BusinessAccountProfileRegistrationView.as_view(), name='profile-register'),
    path('profile/', BusinessAccountProfileView.as_view(), name='profile'),
    path('profile/<uuid:pk>/', OtherBusinessProfileView.as_view(), name='other-business-profile'),

    # Verification management
    path('verification/request/', VerificationRequestCreateView.as_view(), name='verification-request-create'),
    path('verification/requests/', VerificationRequestListView.as_view(), name='verification-request-list'),
    path('verification/requests/<int:pk>/action/', VerificationRequestActionView.as_view(), name='verification-request-action'),
    path('members/', BusinessMemberListView.as_view(), name='member-list'),
    path('members/<uuid:user_id>/remove/', RemoveMemberView.as_view(), name='member-remove'),

    # Recommendation endpoints
    path('recommendations/', RecommendationListView.as_view(), name='recommendation-list'),
    path('recommendations/give/', GiveRecommendationView.as_view(), name='recommendation-give'),
]
