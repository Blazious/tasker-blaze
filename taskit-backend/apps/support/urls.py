from django.urls import path

from .views import (
    MySupportConversationView,
    MySupportTicketsView,
    SupportChatView,
    SupportEscalationView,
    SupportHealthView,
)

urlpatterns = [
    path("", SupportHealthView.as_view(), name="support-health"),
    path("conversation/", MySupportConversationView.as_view(), name="support-conversation"),
    path("chat/", SupportChatView.as_view(), name="support-chat"),
    path("escalate/", SupportEscalationView.as_view(), name="support-escalate"),
    path("tickets/", MySupportTicketsView.as_view(), name="support-tickets"),
]
