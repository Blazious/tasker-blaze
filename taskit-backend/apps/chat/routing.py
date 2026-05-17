from django.urls import path

from .consumers import TaskChatConsumer

websocket_urlpatterns = [
    path("ws/chat/<int:task_id>/", TaskChatConsumer.as_asgi()),
]
