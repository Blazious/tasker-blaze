from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        NEW_BID = "NEW_BID", "New Bid"
        BID_ACCEPTED = "BID_ACCEPTED", "Bid Accepted"
        PAYMENT_RECEIVED = "PAYMENT_RECEIVED", "Payment Received"
        TASK_COMPLETED = "TASK_COMPLETED", "Task Completed"
        NEW_MESSAGE = "NEW_MESSAGE", "New Message"
        REVIEW_RECEIVED = "REVIEW_RECEIVED", "Review Received"
        TASK_DISPUTED = "TASK_DISPUTED", "Task Disputed"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=30, choices=Type.choices)
    title = models.CharField(max_length=255)
    body = models.TextField()
    related_task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.recipient}"
