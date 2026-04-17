from rest_framework import serializers
from .models import Conversation, Message
from users.models import User
from business_account.models import BusinessAccount
from django.contrib.contenttypes.models import ContentType

class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.SerializerMethodField()
    sender_type = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'sender_type', 'text', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender_id', 'sender_type', 'created_at']

    def get_sender_id(self, obj):
        return str(obj.sender_object_id)

    def get_sender_type(self, obj):
        if obj.sender_content_type == ContentType.objects.get_for_model(User):
            return 'user'
        return 'business_account'

class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    post_title = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'status', 'post_title', 'other_participant', 'last_message', 'updated_at']

    def get_other_participant(self, obj):
        request = self.context.get('request')
        user = request.user
        user_id = str(user.id)
        user_ct = ContentType.objects.get_for_model(user)

        # Check if the current user is participant 1 or 2
        if obj.part1_content_type == user_ct and str(obj.part1_object_id) == user_id:
            other = obj.participant2
            other_type = 'user' if isinstance(other, User) else 'business_account'
        else:
            other = obj.participant1
            other_type = 'user' if isinstance(other, User) else 'business_account'

        if not other:
            return None

        # Return a simple dict with other person's info
        return {
            'id': str(other.id),
            'type': other_type,
            'name': f"{other.first_name} {other.last_name}" if hasattr(other, 'first_name') else getattr(other, 'business_name', 'Unknown'),
            'profile_picture': other.profile_picture.url if hasattr(other, 'profile_picture') and other.profile_picture else None
        }

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if msg:
            return MessageSerializer(msg).data
        return None

    def get_post_title(self, obj):
        return obj.post.title if obj.post else "General Inquiry"
