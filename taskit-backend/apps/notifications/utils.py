from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


def send_notification(recipient, notification_type, title, body, related_task=None):
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        body=body,
        related_task=related_task,
    )

    if recipient.is_verified:
        send_mail(
            subject=title,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[recipient.email],
            fail_silently=True,
        )

    return notification
