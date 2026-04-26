from rest_framework import serializers
from .models import Notification, NotificationDevice

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']

class DeviceRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDevice
        fields = ['registration_id', 'name']
        extra_kwargs = {
            'registration_id': {'required': True}
        }
