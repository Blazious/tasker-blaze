from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.payments.models import Transaction
from apps.reviews.models import Review
from apps.tasks.models import Bid, Task

from .models import Notification
from .utils import send_notification


@receiver(post_save, sender=Bid)
def notify_new_bid_or_acceptance(sender, instance, created, **kwargs):
    task = instance.task
    if created:
        send_notification(
            recipient=task.client,
            notification_type=Notification.Type.NEW_BID,
            title=f"New bid on your task: {task.title}",
            body=f"{instance.tasker.full_name} placed a bid of KES {instance.amount}.",
            related_task=task,
        )
        return

    if instance.status == Bid.Status.ACCEPTED:
        send_notification(
            recipient=instance.tasker,
            notification_type=Notification.Type.BID_ACCEPTED,
            title="Your bid was accepted!",
            body="Your bid was accepted! Time to get to work.",
            related_task=task,
        )
        if task.requires_home_visit:
            send_notification(
                recipient=instance.tasker,
                notification_type=Notification.Type.BID_ACCEPTED,
                title="Home visit safety reminder",
                body=(
                    "Remember: this task involves a home visit. Meet in a public spot "
                    "first and share your location with a friend."
                ),
                related_task=task,
            )


@receiver(pre_save, sender=Transaction)
def remember_previous_transaction_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return

    try:
        instance._previous_status = Transaction.objects.get(pk=instance.pk).status
    except Transaction.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Transaction)
def notify_transaction_status_change(sender, instance, **kwargs):
    previous_status = getattr(instance, "_previous_status", None)
    if previous_status == instance.status:
        return

    if instance.status == Transaction.Status.ESCROWED:
        send_notification(
            recipient=instance.tasker,
            notification_type=Notification.Type.PAYMENT_RECEIVED,
            title="Payment secured",
            body="Payment secured. You can start the task.",
            related_task=instance.task,
        )
    elif instance.status == Transaction.Status.RELEASED:
        send_notification(
            recipient=instance.tasker,
            notification_type=Notification.Type.TASK_COMPLETED,
            title="Payment released",
            body=f"KES {instance.tasker_payout} has been released to you.",
            related_task=instance.task,
        )


@receiver(pre_save, sender=Review)
def remember_previous_review_visibility(sender, instance, **kwargs):
    if not instance.pk:
        instance._was_visible = False
        return

    try:
        instance._was_visible = Review.objects.get(pk=instance.pk).is_visible
    except Review.DoesNotExist:
        instance._was_visible = False


@receiver(post_save, sender=Review)
def notify_review_visibility(sender, instance, **kwargs):
    if not instance.is_visible or getattr(instance, "_was_visible", False):
        return

    send_notification(
        recipient=instance.reviewee,
        notification_type=Notification.Type.REVIEW_RECEIVED,
        title="You have a new review",
        body="You have a new review.",
        related_task=instance.task,
    )


@receiver(pre_save, sender=Task)
def remember_previous_task_status(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        return

    try:
        instance._previous_status = Task.objects.get(pk=instance.pk).status
    except Task.DoesNotExist:
        instance._previous_status = None


@receiver(post_save, sender=Task)
def notify_task_dispute(sender, instance, **kwargs):
    previous_status = getattr(instance, "_previous_status", None)
    if instance.status != Task.Status.DISPUTED or previous_status == instance.status:
        return

    recipients = [instance.client]
    if instance.assigned_tasker:
        recipients.append(instance.assigned_tasker)

    for recipient in recipients:
        send_notification(
            recipient=recipient,
            notification_type=Notification.Type.TASK_DISPUTED,
            title="Task dispute raised",
            body="A dispute has been raised for this task. Our team will review it.",
            related_task=instance,
        )

    send_mail(
        subject="Task dispute raised",
        message=f"Task #{instance.id} is disputed: {instance.title}",
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=True,
    )
