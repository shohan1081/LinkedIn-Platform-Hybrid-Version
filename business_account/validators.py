from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import re
from datetime import date


def validate_password_strength(password):
    """
    Validates password strength (min 8 chars, incl. uppercase, lowercase, number, special char).
    """
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password):
        raise ValidationError("Password must contain at least one number.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError("Password must contain at least one special character.")


def validate_email_format(email):
    """
    Validates email format using Django's built-in validator.
    """
    try:
        validate_email(email)
    except ValidationError:
        raise ValidationError("Enter a valid email address.")


def validate_name(name):
    """
    Validates name (only letters and spaces).
    """
    if not re.fullmatch(r"^[A-Za-z\s]+$", name):
        raise ValidationError("Name can only contain letters and spaces.")


def validate_date_of_birth(dob):
    """
    Validates date of birth (not in future).
    """
    if dob > date.today():
        raise ValidationError("Date of birth cannot be in the future.")


def validate_password_match(password, confirm_password):
    """
    Validates that password and confirm password match.
    """
    if password != confirm_password:
        raise ValidationError("Passwords do not match.")


def validate_profile_picture(image):
    """
    Validates profile picture size and format.
    """
    max_size_mb = 2
    if image.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Profile picture cannot be larger than {max_size_mb}MB.")
    
    allowed_formats = ['jpeg', 'png', 'gif']
    if not image.name.split('.')[-1].lower() in allowed_formats:
        raise ValidationError("Invalid image format. Only JPEG, PNG, GIF are allowed.")
