from django.contrib import admin
from .models import Notification, NotificationDevice

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient_object_id')
    readonly_fields = ('created_at',)

@admin.register(NotificationDevice)
class NotificationDeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'registration_id_short', 'active', 'created_at')
    list_filter = ('active', 'created_at')
    search_fields = ('name', 'registration_id', 'object_id')
    readonly_fields = ('created_at',)

    def registration_id_short(self, obj):
        return obj.registration_id[:30] + '...' if len(obj.registration_id) > 30 else obj.registration_id
    registration_id_short.short_description = 'Registration ID'
