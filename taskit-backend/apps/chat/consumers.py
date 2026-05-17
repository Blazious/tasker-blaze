import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

from .models import ChatThread, Message


class TaskChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.task_id = self.scope["url_route"]["kwargs"]["task_id"]
        self.user = await self.get_user_from_token()

        if self.user is None:
            await self.close(code=4001)
            return

        self.thread = await self.get_thread_for_user(self.task_id, self.user.id)
        if self.thread is None:
            await self.close(code=4003)
            return

        self.group_name = f"chat_{self.thread.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON payload."}))
            return

        event_type = payload.get("type", "message")

        if event_type == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "typing_event",
                    "user_id": self.user.id,
                    "sender_name": self.user.full_name,
                    "is_typing": bool(payload.get("is_typing", True)),
                },
            )
            return

        content = payload.get("content", "").strip()
        if not content:
            await self.send(text_data=json.dumps({"error": "Message content is required."}))
            return

        message = await self.create_message(self.thread.id, self.user.id, content)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "message": {
                    "type": "message",
                    "id": message["id"],
                    "client_message_id": payload.get("client_message_id"),
                    "sender_id": self.user.id,
                    "sender_name": self.user.full_name,
                    "content": message["content"],
                    "timestamp": message["timestamp"],
                },
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    async def typing_event(self, event):
        if event["user_id"] == self.user.id:
            return

        await self.send(
            text_data=json.dumps(
                {
                    "type": "typing",
                    "sender_id": event["user_id"],
                    "sender_name": event["sender_name"],
                    "is_typing": event["is_typing"],
                }
            )
        )

    async def get_user_from_token(self):
        query_string = self.scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        if not token:
            return None

        try:
            access_token = AccessToken(token)
        except (InvalidToken, TokenError):
            return None

        user_id = access_token.get("user_id")
        return await self.get_user(user_id)

    @database_sync_to_async
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_thread_for_user(self, task_id, user_id):
        try:
            thread = ChatThread.objects.get(task_id=task_id)
        except ChatThread.DoesNotExist:
            return None

        if not thread.participants.filter(id=user_id).exists():
            return None
        return thread

    @database_sync_to_async
    def create_message(self, thread_id, sender_id, content):
        message = Message.objects.create(
            thread_id=thread_id,
            sender_id=sender_id,
            content=content,
        )
        return {
            "id": message.id,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
        }
