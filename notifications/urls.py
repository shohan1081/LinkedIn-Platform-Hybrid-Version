from django.urls import path
from .views import (
    DeviceRegistrationView,
    NotificationListView,
    MarkNotificationReadView
)

app_name = 'notifications'

urlpatterns = [
    path('devices/', DeviceRegistrationView.as_view(), name='device-register'),
    path('history/', NotificationListView.as_view(), name='notification-list'),
    path('history/<int:pk>/read/', MarkNotificationReadView.as_view(), name='notification-mark-read'),
]
