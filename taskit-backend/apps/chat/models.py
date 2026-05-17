from django.conf import settings
from django.db import models


class ChatThread(models.Model):
    task = models.OneToOneField(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="chat_thread",
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_threads",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Chat for {self.task}"


class Message(models.Model):
    thread = models.ForeignKey(
        ChatThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="chat/images/", blank=True, null=True)
    voice_note = models.FileField(upload_to="chat/voice-notes/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Message from {self.sender} in {self.thread}"
