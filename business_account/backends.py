from django.contrib.auth.backends import BaseBackend
from .models import BusinessAccount
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _

class BusinessAccountBackend(BaseBackend):
    """
    Custom authentication backend for BusinessAccount model.
    Allows BusinessAccount to be authenticated via JWT.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a BusinessAccount using email and password.
        """
        try:
            business_account = BusinessAccount.objects.get(email=username)
        except BusinessAccount.DoesNotExist:
            return None

        if business_account.check_password(password) and self.user_can_authenticate(business_account):
            return business_account

        return None

    def get_user(self, user_id):
        """
        Retrieve a BusinessAccount by ID.
        """
        try:
            return BusinessAccount.objects.get(pk=user_id)
        except BusinessAccount.DoesNotExist:
            return None

    @staticmethod
    def user_can_authenticate(user):
        """
        Check if the user is active.
        """
        is_active = getattr(user, 'is_active', None)
        return is_active or is_active is None

class BusinessAccountAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        try:
            user_id = validated_token["user_id"]
        except KeyError:
            raise AuthenticationFailed(_("Token contained no recognizable user identification"), code="user_not_found")

        try:
            user = BusinessAccount.objects.get(pk=user_id)
        except BusinessAccount.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code="user_not_found")

        if not user.is_active:
            raise AuthenticationFailed(_("User is inactive"), code="user_inactive")

        return user
