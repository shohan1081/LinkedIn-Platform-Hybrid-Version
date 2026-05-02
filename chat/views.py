from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from business_account.backends import MultiModelJWTAuthentication
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from posts.views import standard_response
from users.models import User
from business_account.models import BusinessAccount

class ConversationListView(generics.ListAPIView):
    """
    List all conversations the current user is part of.
    This includes both active chats and pending message requests.
    """
    serializer_class = ConversationSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_ct = ContentType.objects.get_for_model(user)
        
        # Filter where user is participant 1 OR participant 2
        return Conversation.objects.filter(
            (Q(part1_content_type=user_ct) & Q(part1_object_id=user.id)) |
            (Q(part2_content_type=user_ct) & Q(part2_object_id=user.id))
        ).order_by('-updated_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Conversations retrieved successfully",
            data=serializer.data
        )


class DealsConversationListView(generics.ListAPIView):
    """
    Filter and list conversations that are linked to a specific post (deals).
    """
    serializer_class = ConversationSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_ct = ContentType.objects.get_for_model(user)
        
        # Filter where user is participant AND there is a linked post
        return Conversation.objects.filter(
            (Q(part1_content_type=user_ct, part1_object_id=user.id) |
             Q(part2_content_type=user_ct, part2_object_id=user.id)),
            post_object_id__isnull=False
        ).order_by('-updated_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Deal conversations retrieved successfully",
            data=serializer.data
        )

class ConversationStartView(APIView):
    """
    Start a direct conversation with another user or business.
    If a general conversation already exists, it returns that one.
    """
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        other_user_id = request.data.get('user_id')
        if not other_user_id:
            return standard_response(success=False, message="User ID is required.", status_code=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user_ct = ContentType.objects.get_for_model(user)
        
        # Find the other user (User or Business)
        other_user = None
        other_ct = None
        try:
            other_user = User.objects.get(id=other_user_id)
            other_ct = ContentType.objects.get_for_model(User)
        except (User.DoesNotExist, ValidationError):
            try:
                other_user = BusinessAccount.objects.get(id=other_user_id)
                other_ct = ContentType.objects.get_for_model(BusinessAccount)
            except (BusinessAccount.DoesNotExist, ValidationError):
                return standard_response(success=False, message="Other user not found.", status_code=status.HTTP_404_NOT_FOUND)

        if str(user.id) == str(other_user_id):
            return standard_response(success=False, message="You cannot chat with yourself.", status_code=status.HTTP_400_BAD_REQUEST)

        # Check for existing conversation (without a post)
        conv = Conversation.objects.filter(
            Q(part1_content_type=user_ct, part1_object_id=user.id, part2_content_type=other_ct, part2_object_id=other_user.id, post_content_type__isnull=True) |
            Q(part1_content_type=other_ct, part1_object_id=other_user.id, part2_content_type=user_ct, part2_object_id=user.id, post_content_type__isnull=True)
        ).first()

        if not conv:
            conv = Conversation.objects.create(
                part1_content_type=user_ct,
                part1_object_id=user.id,
                part2_content_type=other_ct,
                part2_object_id=other_user.id,
                status='active' # Direct chats are active by default
            )

        serializer = ConversationSerializer(conv, context={'request': request})
        return standard_response(
            success=True,
            message="Conversation started",
            data=serializer.data
        )

class MessageListView(generics.ListCreateAPIView):
    """
    List messages in a conversation and send new ones.
    """
    serializer_class = MessageSerializer
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get_conversation(self):
        conv_id = self.kwargs.get('pk')
        user = self.request.user
        user_ct = ContentType.objects.get_for_model(user)
        
        try:
            conv = Conversation.objects.get(pk=conv_id)
            # Verify user is a participant
            is_p1 = conv.part1_content_type == user_ct and str(conv.part1_object_id) == str(user.id)
            is_p2 = conv.part2_content_type == user_ct and str(conv.part2_object_id) == str(user.id)
            
            if not (is_p1 or is_p2):
                return None
            return conv
        except Conversation.DoesNotExist:
            return None

    def get_queryset(self):
        conv = self.get_conversation()
        if conv:
            return conv.messages.all()
        return Message.objects.none()

    def list(self, request, *args, **kwargs):
        conv = self.get_conversation()
        if not conv:
            return standard_response(success=False, message="Conversation not found or unauthorized.", status_code=status.HTTP_404_NOT_FOUND)
        
        # Mark messages as read for the current user
        user = request.user
        user_ct = ContentType.objects.get_for_model(user)
        conv.messages.exclude(sender_content_type=user_ct, sender_object_id=user.id).update(is_read=True)

        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return standard_response(
            success=True,
            message="Messages retrieved successfully",
            data={
                'conversation_status': conv.status,
                'messages': serializer.data
            }
        )

    def create(self, request, *args, **kwargs):
        conv = self.get_conversation()
        if not conv:
            return standard_response(success=False, message="Conversation not found or unauthorized.", status_code=status.HTTP_404_NOT_FOUND)
        
        if conv.status != 'active':
            return standard_response(
                success=False, 
                message="Cannot send messages until the connection request is accepted.", 
                status_code=status.HTTP_403_FORBIDDEN
            )

        user = request.user
        user_ct = ContentType.objects.get_for_model(user)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            conversation=conv,
            sender_content_type=user_ct,
            sender_object_id=user.id
        )
        
        # Update conversation timestamp
        conv.save() # Triggers auto_now update

        return standard_response(
            success=True,
            message="Message sent",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

class ConversationActionView(APIView):
    """
    Accept a message request (Alternative to using the Proposal Action API).
    """
    authentication_classes = [MultiModelJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        user_ct = ContentType.objects.get_for_model(user)
        
        try:
            # Only participant 1 (post owner) can usually 'accept' a request
            conv = Conversation.objects.get(pk=pk, part1_content_type=user_ct, part1_object_id=user.id)
        except Conversation.DoesNotExist:
            return standard_response(success=False, message="Request not found.", status_code=status.HTTP_404_NOT_FOUND)

        action = request.data.get('action') # 'accept'
        if action == 'accept':
            conv.status = 'active'
            conv.save()
            return standard_response(success=True, message="Message request accepted. You can now chat.")
        
        return standard_response(success=False, message="Invalid action.", status_code=status.HTTP_400_BAD_REQUEST)
