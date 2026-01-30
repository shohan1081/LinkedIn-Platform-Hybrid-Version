import random
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def generate_otp():
    """Generate a 4-digit OTP"""
    return str(random.randint(1000, 9999))


def send_otp_email(business_account, otp):
    """Send OTP to business account's email"""
    try:
        subject = 'Your OTP for Business Account Verification'
        html_message = render_to_string('emails/otp_email.html', {'otp': otp, 'user_email': business_account.email})
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = business_account.email

        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"OTP sent to {business_account.email}")
    except Exception as e:
        logger.error(f"Error sending OTP to {business_account.email}: {e}")
        # In production, you might want to re-raise or handle this more gracefully
        pass


def send_welcome_email(business_account):
    """Send a welcome email to the new business account"""
    try:
        subject = 'Welcome to Our Platform!'
        html_message = render_to_string('emails/welcome.html', {'user_email': business_account.email})
        plain_message = strip_tags(html_message)
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = business_account.email

        send_mail(
            subject,
            plain_message,
            from_email,
            [to_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Welcome email sent to {business_account.email}")
    except Exception as e:
        logger.error(f"Error sending welcome email to {business_account.email}: {e}")
        pass


def get_client_ip(request):
    """Get the client's IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """Get the user agent string"""
    return request.META.get('HTTP_USER_AGENT', '')
