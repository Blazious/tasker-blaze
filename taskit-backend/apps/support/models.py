from django.conf import settings
from django.db import models


class SupportConversation(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_conversations",
    )
    title = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title or f"Support chat with {self.user}"


class SupportMessage(models.Model):
    class Sender(models.TextChoices):
        USER = "USER", "User"
        BOT = "BOT", "Bot"
        ADMIN = "ADMIN", "Admin"

    conversation = models.ForeignKey(
        SupportConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.CharField(max_length=10, choices=Sender.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} message in {self.conversation_id}"


class SupportTicket(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        REVIEWING = "REVIEWING", "Reviewing"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        NORMAL = "NORMAL", "Normal"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )
    conversation = models.ForeignKey(
        SupportConversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )
    title = models.CharField(max_length=160)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.status}"
