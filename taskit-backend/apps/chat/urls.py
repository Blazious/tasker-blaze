from django.urls import path

from .views import ChatHealthView, MyThreadsView, TaskMessagesView

urlpatterns = [
    path("", ChatHealthView.as_view(), name="chat-health"),
    path("my-threads/", MyThreadsView.as_view(), name="my-chat-threads"),
    path("<int:task_id>/messages/", TaskMessagesView.as_view(), name="task-messages"),
]
