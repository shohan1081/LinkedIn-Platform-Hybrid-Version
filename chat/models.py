from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
import uuid

class Conversation(models.Model):
    """
    Represents a chat thread between two parties regarding a specific post.
    Participants can be standard Users or BusinessAccounts.
    """
    STATUS_CHOICES = [
        ('pending', 'Message Request'),
        ('active', 'Active Chat'),
        ('blocked', 'Blocked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Participant 1 (usually the post owner)
    part1_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='conversation_part1')
    part1_object_id = models.UUIDField()
    participant1 = GenericForeignKey('part1_content_type', 'part1_object_id')

    # Participant 2 (usually the proposer)
    part2_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='conversation_part2')
    part2_object_id = models.UUIDField()
    participant2 = GenericForeignKey('part2_content_type', 'part2_object_id')

    # Related Post (Generic FK to NeedPost or OfferPost)
    post_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    post_object_id = models.UUIDField(null=True, blank=True)
    post = GenericForeignKey('post_content_type', 'post_object_id')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        # Ensure only one conversation exists between same two parties for same post
        unique_together = ('part1_content_type', 'part1_object_id', 'part2_content_type', 'part2_object_id', 'post_content_type', 'post_object_id')

    def __str__(self):
        return f"Chat between {self.participant1} and {self.participant2}"

class Message(models.Model):
    """
    An individual message within a conversation.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    
    # Sender (Generic FK)
    sender_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    sender_object_id = models.UUIDField()
    sender = GenericForeignKey('sender_content_type', 'sender_object_id')

    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender} at {self.created_at}"
