from rest_framework import serializers
from .models import Conversation, Message
from users.models import User
from business_account.models import BusinessAccount
from django.contrib.contenttypes.models import ContentType

class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.SerializerMethodField()
    sender_type = serializers.SerializerMethodField()
    sender_name = serializers.SerializerMethodField()
    sender_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender_id', 'sender_type', 'sender_name', 'sender_profile_picture', 'text', 'is_read', 'created_at']
        read_only_fields = ['id', 'sender_id', 'sender_type', 'sender_name', 'sender_profile_picture', 'created_at']

    def get_sender_id(self, obj):
        return str(obj.sender_object_id)

    def get_sender_type(self, obj):
        if obj.sender_content_type == ContentType.objects.get_for_model(User):
            return 'user'
        return 'business_account'

    def get_sender_name(self, obj):
        sender = obj.sender
        if not sender:
            return "Unknown"
        if isinstance(sender, User):
            return f"{sender.first_name} {sender.last_name}".strip() or sender.email
        return getattr(sender, 'business_name', 'Unknown') or sender.email

    def get_sender_profile_picture(self, obj):
        sender = obj.sender
        if not sender:
            return None
        
        request = self.context.get('request')
        pic = None
        if isinstance(sender, User):
            pic = sender.profile_picture
        else:
            # BusinessAccount
            pic = getattr(sender, 'profile_picture', None)

        if pic:
            if request:
                return request.build_absolute_uri(pic.url)
            return pic.url
        return None

class ConversationSerializer(serializers.ModelSerializer):
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    post_title = serializers.SerializerMethodField()
    post_id = serializers.SerializerMethodField()
    post_type = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'status', 'post_title', 'post_id', 'post_type', 'other_participant', 'last_message', 'unread_count', 'updated_at']

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        
        user = request.user
        user_ct = ContentType.objects.get_for_model(user)
        
        # Count messages in this conversation that are NOT read and NOT sent by the current user
        return obj.messages.filter(is_read=False).exclude(
            sender_content_type=user_ct,
            sender_object_id=user.id
        ).count()

    def get_other_participant(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None

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

        # Determine the name
        if isinstance(other, User):
            name = f"{other.first_name} {other.last_name}".strip() or other.email
        else:
            name = getattr(other, 'business_name', 'Unknown') or other.email

        # Determine profile picture
        pic_url = None
        pic = getattr(other, 'profile_picture', None)
        if pic:
            pic_url = request.build_absolute_uri(pic.url) if request else pic.url

        return {
            'id': str(other.id),
            'type': other_type,
            'name': name,
            'profile_picture': pic_url
        }

    def get_last_message(self, obj):
        msg = obj.messages.last()
        if msg:
            # Pass context for absolute URLs
            return MessageSerializer(msg, context=self.context).data
        return None

    def get_post_title(self, obj):
        return obj.post.title if obj.post else "General Inquiry"

    def get_post_id(self, obj):
        return str(obj.post_object_id) if obj.post_object_id else None

    def get_post_type(self, obj):
        if not obj.post_content_type:
            return None
        from posts.models import NeedPost
        if obj.post_content_type == ContentType.objects.get_for_model(NeedPost):
            return 'need'
        return 'offer'
