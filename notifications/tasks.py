from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from .models import NotificationDevice
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_push_notification_task(recipient_ct_id, recipient_id, title, message, extra_data=None):
    """
    Background task to send push notifications via Firebase.
    Iterates through all active devices for the recipient.
    """
    try:
        recipient_ct = ContentType.objects.get_for_id(recipient_ct_id)
        
        # Find all active devices for this recipient (User or BusinessAccount)
        devices = NotificationDevice.objects.filter(
            content_type=recipient_ct,
            object_id=recipient_id,
            active=True
        )
        
        if not devices.exists():
            logger.info(f"No active devices found for recipient {recipient_id}")
            return
            
        success_count = 0
        for device in devices:
            try:
                device.send_message(message, title=title, data=extra_data)
                success_count += 1
            except Exception as device_error:
                logger.error(f"Failed to send to device {device.id}: {device_error}")
        
        logger.info(f"Push notification sent to {success_count}/{devices.count()} devices for recipient {recipient_id}")
        
    except Exception as e:
        logger.error(f"Error in send_push_notification_task: {str(e)}")
