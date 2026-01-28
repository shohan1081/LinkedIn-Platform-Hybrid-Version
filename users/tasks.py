from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@shared_task
def send_otp_email_task(user_email, otp):
    """
    Celery task to send OTP to user's email
    """
    try:
        subject = 'Your One-Time Password (OTP)'
        html_message = render_to_string('emails/otp_email.html', {
            'otp': otp,
            'site_name': 'Your App Name',
        })
        plain_message = strip_tags(html_message)
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )
        return "OTP email sent successfully."
    except Exception as e:
        return f"Error sending OTP email: {str(e)}"