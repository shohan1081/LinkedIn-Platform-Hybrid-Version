from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.contenttypes.models import ContentType

from business_account.backends import MultiModelJWTAuthentication
from .models import Notification, NotificationDevice
from .serializers import NotificationSerializer, DeviceRegistrationSerializer


def standard_response(
    success=True,
    message="",
    data=None,
    errors=None,
    status_code=status.HTTP_200_OK
):
    return Response(
        {
            "success": success,
            "message": message,
            "data": data,
            "errors": errors,
        },
        status=status_code,
    )


class DeviceRegistrationView(APIView):
    """
    Register or update a device token for push notifications.
    Supports both User and BusinessAccount via GenericForeignKey.

    Fixes:
    - Prevents duplicate device rows
    - Updates token when Firebase refreshes it
    - Deactivates old tokens for the same device
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]
    serializer_class = DeviceRegistrationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            reg_id = serializer.validated_data["registration_id"]
            device_name = serializer.validated_data.get("name", "").strip()

            user_ct = ContentType.objects.get_for_model(request.user)

            # Deactivate any old token rows for same owner + same device
            NotificationDevice.objects.filter(
                content_type=user_ct,
                object_id=request.user.id,
                name=device_name,
            ).exclude(
                registration_id=reg_id
            ).update(active=False)

            # Update existing device OR create new one
            device, created = NotificationDevice.objects.update_or_create(
                content_type=user_ct,
                object_id=request.user.id,
                name=device_name,
                defaults={
                    "registration_id": reg_id,
                    "active": True,
                },
            )

            message = (
                "Device registered successfully"
                if created
                else "Device token updated successfully"
            )

            return standard_response(
                success=True,
                message=message,
            )

        return standard_response(
            success=False,
            message="Registration failed",
            errors=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class NotificationListView(APIView):
    """
    Get notification history for authenticated User / BusinessAccount.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def get(self, request):
        recipient_ct = ContentType.objects.get_for_model(request.user)

        notifications = Notification.objects.filter(
            recipient_content_type=recipient_ct,
            recipient_object_id=request.user.id,
        )

        serializer = NotificationSerializer(notifications, many=True)

        return standard_response(
            success=True,
            message="Notifications retrieved successfully",
            data=serializer.data,
        )


class MarkNotificationReadView(APIView):
    """
    Mark a notification as read.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def post(self, request, pk):
        recipient_ct = ContentType.objects.get_for_model(request.user)

        try:
            notification = Notification.objects.get(
                pk=pk,
                recipient_content_type=recipient_ct,
                recipient_object_id=request.user.id,
            )

            notification.is_read = True
            notification.save(update_fields=["is_read"])

            return standard_response(
                success=True,
                message="Notification marked as read",
            )

        except Notification.DoesNotExist:
            return standard_response(
                success=False,
                message="Notification not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )


class NotificationDeleteView(APIView):
    """
    Delete a specific notification.
    """

    permission_classes = [IsAuthenticated]
    authentication_classes = [MultiModelJWTAuthentication]

    def delete(self, request, pk):
        recipient_ct = ContentType.objects.get_for_model(request.user)

        try:
            notification = Notification.objects.get(
                pk=pk,
                recipient_content_type=recipient_ct,
                recipient_object_id=request.user.id,
            )
            notification.delete()
            return standard_response(
                success=True,
                message="Notification deleted successfully",
            )
        except Notification.DoesNotExist:
            return standard_response(
                success=False,
                message="Notification not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

