from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .gemini import TaskitSupportBot
from .models import SupportConversation, SupportMessage, SupportTicket
from .serializers import (
    SupportChatRequestSerializer,
    SupportConversationSerializer,
    SupportEscalationSerializer,
    SupportTicketSerializer,
)


class SupportHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "app": "support",
                "status": "ok",
                "gemini_configured": bool(getattr(settings, "GEMINI_API_KEY", "")),
                "gemini_model": getattr(settings, "GEMINI_MODEL", ""),
            }
        )


class MySupportConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        conversation = (
            SupportConversation.objects.filter(user=request.user)
            .prefetch_related("messages")
            .first()
        )
        if not conversation:
            conversation = SupportConversation.objects.create(
                user=request.user,
                title="TaskiT Assistant",
            )
        return Response(SupportConversationSerializer(conversation).data)


class SupportChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SupportChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = self.get_conversation(request.user, serializer.validated_data.get("conversation_id"))

        user_message = SupportMessage.objects.create(
            conversation=conversation,
            sender=SupportMessage.Sender.USER,
            content=serializer.validated_data["message"],
        )

        history = list(conversation.messages.exclude(pk=user_message.pk).order_by("-created_at")[:8])
        history.reverse()
        result = TaskitSupportBot().answer(request.user, user_message.content, history)

        bot_message = SupportMessage.objects.create(
            conversation=conversation,
            sender=SupportMessage.Sender.BOT,
            content=result["answer"],
        )

        ticket = None
        if result.get("needs_escalation"):
            ticket = SupportTicket.objects.create(
                user=request.user,
                conversation=conversation,
                title=result.get("ticket_title") or "TaskiT support request",
                description=f"User message: {user_message.content}\n\nAssistant answer: {bot_message.content}",
                priority=result.get("priority") or SupportTicket.Priority.NORMAL,
            )
            self.notify_admin(ticket)

        return Response(
            {
                "conversation_id": conversation.id,
                "user_message": SupportConversationSerializer().fields["messages"].child.to_representation(user_message),
                "bot_message": SupportConversationSerializer().fields["messages"].child.to_representation(bot_message),
                "ticket": SupportTicketSerializer(ticket).data if ticket else None,
            },
            status=status.HTTP_201_CREATED,
        )

    def get_conversation(self, user, conversation_id=None):
        if conversation_id:
            return get_object_or_404(SupportConversation, pk=conversation_id, user=user)
        conversation, _ = SupportConversation.objects.get_or_create(
            user=user,
            defaults={"title": "TaskiT Assistant"},
        )
        return conversation

    def notify_admin(self, ticket):
        admin_email = getattr(settings, "ADMIN_EMAIL", "")
        if not admin_email:
            return
        send_mail(
            subject=f"TaskiT support ticket: {ticket.title}",
            message=f"{ticket.description}\n\nPriority: {ticket.priority}",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[admin_email],
            fail_silently=True,
        )


class SupportEscalationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SupportEscalationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = None
        if serializer.validated_data.get("conversation_id"):
            conversation = get_object_or_404(
                SupportConversation,
                pk=serializer.validated_data["conversation_id"],
                user=request.user,
            )
        ticket = SupportTicket.objects.create(
            user=request.user,
            conversation=conversation,
            title=serializer.validated_data["title"],
            description=serializer.validated_data["description"],
            priority=serializer.validated_data["priority"],
        )
        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class MySupportTicketsView(generics.ListAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)
