import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.contenttypes.models import ContentType
from .models import Conversation, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f"chat_{self.conversation_id}"

        # Reject if user is not authenticated
        if self.user.is_anonymous:
            await self.close()
            return

        # Verify user is participant of this conversation
        if not await self.is_participant():
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid JSON format. Please send a JSON object like {"message": "your text"}'
            }))
            return

        message_text = data.get('message')

        if not message_text:
            return

        # Save message to database
        saved_msg = await self.save_message(message_text)

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_text,
                'sender_id': str(self.user.id),
                'sender_type': 'user' if hasattr(self.user, 'first_name') else 'business_account',
                'created_at': str(saved_msg.created_at)
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_type': event['sender_type'],
            'created_at': event['created_at']
        }))

    @database_sync_to_async
    def is_participant(self):
        try:
            conv = Conversation.objects.get(id=self.conversation_id)
            user_id = str(self.user.id)
            # Both participant IDs are UUIDs, compare as strings
            is_p1 = str(conv.part1_object_id) == user_id
            is_p2 = str(conv.part2_object_id) == user_id
            return is_p1 or is_p2
        except Exception:
            return False

    @database_sync_to_async
    def save_message(self, text):
        conv = Conversation.objects.get(id=self.conversation_id)
        user_ct = ContentType.objects.get_for_model(self.user)
        
        # Update conversation timestamp
        conv.save() 

        return Message.objects.create(
            conversation=conv,
            sender_content_type=user_ct,
            sender_object_id=self.user.id,
            text=text
        )
