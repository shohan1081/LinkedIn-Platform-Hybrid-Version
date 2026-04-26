from django.contrib.contenttypes.models import ContentType
from .models import Notification
from .tasks import send_push_notification_task

def create_notification(recipient, title, message, notification_type, target=None):
    """
    Creates an in-app notification and triggers a push notification.
    
    Args:
        recipient: User or BusinessAccount instance
        title: Notification title
        message: Notification message body
        notification_type: Type from Notification.NOTIFICATION_TYPES
        target: Optional object that triggered the notification
    """
    recipient_ct = ContentType.objects.get_for_model(recipient)
    
    # Create in-app notification record
    notification = Notification.objects.create(
        recipient_content_type=recipient_ct,
        recipient_object_id=recipient.id,
        title=title,
        message=message,
        notification_type=notification_type
    )
    
    if target:
        notification.target_content_type = ContentType.objects.get_for_model(target)
        notification.target_object_id = str(target.id)
        notification.save()

    # Trigger async push notification
    send_push_notification_task.delay(
        str(recipient_ct.id),
        str(recipient.id),
        title,
        message,
        {'notification_id': str(notification.id), 'type': notification_type}
    )
    
    return notification
