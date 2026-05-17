from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatThread, Message
from .serializers import ChatThreadSerializer, MessageSerializer


class ChatHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"app": "chat", "status": "ok"})


class ThreadAccessMixin:
    def get_thread(self):
        thread = get_object_or_404(
            ChatThread.objects.select_related("task").prefetch_related("participants"),
            task_id=self.kwargs["task_id"],
        )
        if not thread.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied("You are not a participant in this chat.")
        return thread


class TaskMessagesView(ThreadAccessMixin, generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        thread = self.get_thread()
        return thread.messages.select_related("sender").all()

    def list(self, request, *args, **kwargs):
        thread = self.get_thread()
        Message.objects.filter(thread=thread).exclude(sender=request.user).update(
            is_read=True
        )
        queryset = thread.messages.select_related("sender").all()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        thread = self.get_thread()
        Message.objects.filter(thread=thread).exclude(sender=request.user).update(
            is_read=True
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(thread=thread, sender=request.user)
        return Response(
            self.get_serializer(message).data,
            status=status.HTTP_201_CREATED,
        )


class MyThreadsView(generics.ListAPIView):
    serializer_class = ChatThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            ChatThread.objects.filter(participants=self.request.user)
            .select_related("task")
            .prefetch_related("messages__sender", "participants")
            .distinct()
        )
