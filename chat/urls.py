from django.urls import path
from .views import (
    ConversationListView,
    DealsConversationListView,
    ConversationStartView,
    MessageListView,
    ConversationActionView,
)

app_name = 'chat'

urlpatterns = [
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('conversations/deals/', DealsConversationListView.as_view(), name='deals-conversation-list'),
    path('conversations/start/', ConversationStartView.as_view(), name='conversation-start'),
    path('conversations/<uuid:pk>/messages/', MessageListView.as_view(), name='message-list'),
    path('conversations/<uuid:pk>/action/', ConversationActionView.as_view(), name='conversation-action'),
]
