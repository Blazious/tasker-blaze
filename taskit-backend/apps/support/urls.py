from django.urls import path

from .views import (
    AdminSupportTicketDetailView,
    AdminSupportTicketListView,
    MySupportConversationView,
    MySupportTicketsView,
    AdminOverviewView,
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
    path("admin/overview/", AdminOverviewView.as_view(), name="admin-overview"),
    path("admin/tickets/", AdminSupportTicketListView.as_view(), name="admin-support-tickets"),
    path("admin/tickets/<int:pk>/", AdminSupportTicketDetailView.as_view(), name="admin-support-ticket-detail"),
]
