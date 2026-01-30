from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid

from .managers import BusinessAccountManager


class BusinessAccount(AbstractBaseUser, PermissionsMixin):
    """
    Custom Business Account Model
    Uses email as the unique identifier
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for the business account")
    )

    email = models.EmailField(
        _('email address'),
        unique=True,
        max_length=255,
        db_index=True,
        help_text=_("Business account's email address (used for login)")
    )

    # Business specific fields
    role_position = models.CharField(_('role/position'), max_length=150, blank=True, null=True)
    business_name = models.CharField(_('business name'), max_length=255, blank=True, null=True)
    industry_category = models.CharField(_('industry/category'), max_length=150, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)

    # Status fields
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_("Designates whether this business account should be treated as active.")
    )

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_("Designates whether the business account can log into admin site.")
    )

    is_email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_("Designates whether business account's email has been verified")
    )

    is_profile_complete = models.BooleanField(
        _('profile complete'),
        default=False,
        help_text=_("Designates whether the business account has completed their profile registration")
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        _('date joined'),
        default=timezone.now,
        help_text=_("Date when business account registered")
    )

    last_login = models.DateTimeField(
        _('last login'),
        null=True,
        blank=True,
        help_text=_("Date of business account's last login")
    )

    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_("Last time business account data was updated")
    )

    # OTP fields
    otp = models.CharField(max_length=4, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = BusinessAccountManager()

    class Meta:
        verbose_name = _('business account')
        verbose_name_plural = _('business accounts')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active', 'is_email_verified']),
        ]

    def __str__(self):
        return self.email

    def is_otp_valid(self, expiry_minutes=10):
        if not self.otp_created_at:
            return False
        expiry_time = self.otp_created_at + timezone.timedelta(minutes=expiry_minutes)
        return timezone.now() < expiry_time

    def clear_otp(self):
        self.otp = None
        self.otp_created_at = None
        self.save(update_fields=['otp', 'otp_created_at'])