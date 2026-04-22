from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .managers import UserManager
import uuid
from django.contrib.auth.hashers import make_password, check_password


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User Model
    Uses email as the unique identifier instead of username
    """
    
    # Primary identifier (UUID for better security)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for the user")
    )
    
    # Required fields
    email = models.EmailField(
        _('email address'),
        unique=True,
        max_length=255,
        db_index=True,
        help_text=_("User's email address (used for login)")
    )
    
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    
    date_of_birth = models.DateField(
        _('date of birth'),
        null=True,
        blank=True,
        help_text=_("User's date of birth")
    )

    address = models.CharField(max_length=255, blank=True, null=True)
    address_line_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
   
    gender = models.CharField(
        _('gender'),
        max_length=20,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say'),
        ],
        null=True,
        blank=True,
        help_text=_("User's gender")
    )

    occupation = models.CharField(
        _('occupation'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("User's occupation")
    )

    country = models.CharField(
        _('country'),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("User's country")
    )
    
    # Status fields
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_("Designates whether this user should be treated as active.")
    )
    
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_("Designates whether the user can log into admin site.")
    )
    
    is_email_verified = models.BooleanField(
        _('email verified'),
        default=False,
        help_text=_("Designates whether user's email has been verified")
    )

    is_subscribed = models.BooleanField(
        _('subscribed'),
        default=False,
        help_text=_("Designates whether the user has an active subscription")
    )

    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        help_text=_("Designates whether the user has been verified by a business account")
    )

    is_profile_complete = models.BooleanField(
        _('profile complete'),
        default=False,
        help_text=_("Designates whether the user has completed their profile registration")
    )
    
    headline = models.CharField(
        _('headline'),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("A short headline or status for the user's profile")
    )

    # Profile picture
    profile_picture = models.ImageField(
        _('profile picture'),
        upload_to='profile_pictures/',
        null=True,
        blank=True,
        help_text=_("User's profile picture")
    )

    cover_photo = models.ImageField(
        _('cover photo'),
        upload_to='cover_photos/',
        null=True,
        blank=True,
        help_text=_("User's cover photo")
    )

    about = models.TextField(
        _('about'),
        null=True,
        blank=True,
        help_text=_("User's about section")
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        _('date joined'),
        default=timezone.now,
        help_text=_("Date when user registered")
    )
    
    last_login = models.DateTimeField(
        _('last login'),
        null=True,
        blank=True,
        help_text=_("Date of user's last login")
    )
    
    updated_at = models.DateTimeField(
        _('updated at'),
        auto_now=True,
        help_text=_("Last time user data was updated")
    )

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='user_set_custom',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='user_permissions_custom',
        related_query_name='user',
    )
    
    # OTP fields
    otp = models.CharField(max_length=4, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    # journal_pin = models.CharField(max_length=128, null=True, blank=True)

    preferred_language = models.CharField(
        max_length=10,
        choices=[('en', 'English'), ('hi', 'Hindi'), ('pt', 'Portuguese')],
        default='en',
        help_text=_("User's preferred language for API responses")
    )

    # Set email as the unique identifier
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # No extra fields required for superuser creation
    
    # Use custom manager
    objects = UserManager()
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active', 'is_email_verified']),
        ]
    
    def __str__(self):
        """String representation of user"""
        return self.email
    
    def get_full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return user's first name"""
        return self.first_name

    def is_otp_valid(self, expiry_minutes=10):
        """
        Check if OTP is still valid
        
        Args:
            expiry_minutes (int): Number of minutes before OTP expires
            
        Returns:
            bool: True if OTP is valid, False otherwise
        """
        if not self.otp_created_at:
            return False
        
        expiry_time = self.otp_created_at + timezone.timedelta(minutes=expiry_minutes)
        return timezone.now() < expiry_time

    def clear_otp(self):
        """Clear OTP after successful verification"""
        self.otp = None
        self.otp_created_at = None
        self.save(update_fields=['otp', 'otp_created_at'])



class AccountDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Deletion request for {self.email}"

class ProfileDataDeletionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile data deletion request for {self.email}"

class UserLoginHistory(models.Model):
    """
    Track user login history for security purposes
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        help_text=_("User who logged in")
    )
    
    login_time = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Time of login")
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_("IP address used for login")
    )
    
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text=_("Browser/device user agent string")
    )
    
    class Meta:
        verbose_name = _('login history')
        verbose_name_plural = _('login histories')
        ordering = ['-login_time']
        indexes = [
            models.Index(fields=['user', '-login_time']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.login_time}"


class Education(models.Model):
    """
    Model to store user's education history
    Only applicable for regular Users, not BusinessAccounts
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='educations',
        help_text=_("User this education belongs to")
    )
    school = models.CharField(_('school'), max_length=255)
    degree = models.CharField(_('degree'), max_length=255)
    field_of_study = models.CharField(_('field of study'), max_length=255)
    grade = models.CharField(_('grade'), max_length=100, blank=True, null=True)
    activities_and_societies = models.TextField(_('activities and societies'), blank=True, null=True)
    description = models.TextField(_('description'), blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('education')
        verbose_name_plural = _('educations')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.degree} at {self.school} - {self.user.email}"


class Experience(models.Model):
    """
    Model to store user's work experience
    Only applicable for regular Users, not BusinessAccounts
    """
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('self_employed', 'Self-employed'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
        ('trainee', 'Trainee'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='experiences',
        help_text=_("User this experience belongs to")
    )
    title = models.CharField(_('title'), max_length=255)
    company = models.CharField(_('company'), max_length=255)
    employment_type = models.CharField(
        _('employment type'),
        max_length=50,
        choices=EMPLOYMENT_TYPE_CHOICES,
        blank=True,
        null=True
    )
    start_date = models.DateField(_('start date'))
    end_date = models.DateField(_('end date'), blank=True, null=True)
    location = models.CharField(_('location'), max_length=255, blank=True, null=True)
    description = models.TextField(_('description'), blank=True, null=True)
    skills = models.JSONField(_('skills'), default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('experience')
        verbose_name_plural = _('experiences')
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} at {self.company} - {self.user.email}"
