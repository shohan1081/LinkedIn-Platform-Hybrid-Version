from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

class Notification(models.Model):
    """
    Model to store in-app notification history.
    Supports both User and BusinessAccount using GenericForeignKey.
    """
    NOTIFICATION_TYPES = [
        ('chat_message', 'New Chat Message'),
        ('recommendation', 'New Recommendation'),
        ('verification_request', 'New Verification Request'),
        ('verification_update', 'Verification Status Update'),
        ('post_proposal', 'New Post Proposal'),
        ('system_alert', 'System Alert'),
    ]

    # The recipient of the notification (User or BusinessAccount)
    recipient_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.CASCADE, 
        related_name='notifications_received'
    )
    recipient_object_id = models.UUIDField()
    recipient = GenericForeignKey('recipient_content_type', 'recipient_object_id')

    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    
    # Reference to the object that triggered the notification (e.g., Message, Recommendation)
    target_content_type = models.ForeignKey(
        ContentType, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='notification_targets'
    )
    target_object_id = models.CharField(max_length=255, null=True, blank=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient_content_type', 'recipient_object_id']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.title} for {self.recipient}"

class NotificationDevice(models.Model):
    """
    Custom Device model to support both User and BusinessAccount.
    """
    # The owner of the device (User or BusinessAccount)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    user = GenericForeignKey('content_type', 'object_id')

    registration_id = models.TextField(unique=True, verbose_name=_("Registration ID"))
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Device Name"))
    active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['registration_id']),
        ]

    def __str__(self):
        return f"{self.name or 'Device'} - {self.user}"

    def send_message(self, message, title=None, data=None):
        """
        Send a push notification to this specific device using Firebase Admin SDK.
        """
        from firebase_admin import messaging
        
        notification = messaging.Notification(
            title=title,
            body=message,
        )
        
        message_obj = messaging.Message(
            notification=notification,
            data=data or {},
            token=self.registration_id,
        )
        
        try:
            return messaging.send(message_obj)
        except Exception as e:
            # If token is invalid, deactivate the device
            if "registration-token-not-registered" in str(e).lower():
                self.active = False
                self.save()
            raise e
