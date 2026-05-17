from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction as db_transaction
from django.utils import timezone

from apps.notifications.utils import send_notification
from apps.notifications.models import Notification
from apps.tasks.models import Task

from .billing import track_platform_fee
from .econfirm import EconfirmClient
from .models import EscrowLedger, Transaction


@db_transaction.atomic
def hold_funds(transaction):
    now = timezone.now()
    task = transaction.task

    transaction.status = Transaction.Status.ESCROWED
    transaction.paid_at = now
    transaction.save(update_fields=["status", "paid_at", "updated_at"])

    task.status = Task.Status.IN_PROGRESS
    task.save(update_fields=["status", "updated_at"])

    EscrowLedger.objects.create(
        transaction=transaction,
        action=EscrowLedger.Action.HOLD,
        amount=transaction.agreed_amount,
    )

    send_notification(
        transaction.client,
        Notification.Type.PAYMENT_RECEIVED,
        "Payment confirmed",
        "Payment confirmed. Funds are held in escrow.",
        related_task=task,
    )
    send_notification(
        transaction.tasker,
        Notification.Type.PAYMENT_RECEIVED,
        "Payment confirmed",
        "Payment confirmed. You can start the task.",
        related_task=task,
    )
    return transaction


@db_transaction.atomic
def release_funds(transaction):
    if transaction.status != Transaction.Status.ESCROWED:
        raise ValueError("Only escrowed transactions can be released.")

    if transaction.econfirm_transaction_id:
        EconfirmClient().release_funds(transaction)

    now = timezone.now()
    task = transaction.task

    transaction.status = Transaction.Status.RELEASED
    transaction.released_at = now
    transaction.save(update_fields=["status", "released_at", "updated_at"])

    task.status = Task.Status.COMPLETED
    task.completed_at = now
    task.save(update_fields=["status", "completed_at", "updated_at"])

    EscrowLedger.objects.create(
        transaction=transaction,
        action=EscrowLedger.Action.RELEASE,
        amount=transaction.tasker_payout,
        note="Tasker payout",
    )
    track_platform_fee(transaction)

    send_notification(
        transaction.tasker,
        Notification.Type.TASK_COMPLETED,
        "Payout processing",
        f"KES {transaction.tasker_payout} is being released to your eConfirm payout wallet.",
        related_task=task,
    )
    return transaction


@db_transaction.atomic
def refund_client(transaction):
    if transaction.status != Transaction.Status.ESCROWED:
        raise ValueError("Only escrowed transactions can be refunded.")

    EconfirmClient().refund_funds(transaction, "Task cancelled or refunded by TaskiT")

    task = transaction.task
    transaction.status = Transaction.Status.REFUNDED
    transaction.save(update_fields=["status", "updated_at"])

    task.status = Task.Status.CANCELLED
    task.save(update_fields=["status", "updated_at"])

    EscrowLedger.objects.create(
        transaction=transaction,
        action=EscrowLedger.Action.REFUND,
        amount=transaction.total_charged,
    )
    send_notification(
        transaction.client,
        Notification.Type.PAYMENT_RECEIVED,
        "Refund processing",
        f"Your KES {transaction.total_charged} is being refunded",
        related_task=task,
    )
    # TODO: Trigger actual M-Pesa refund via Pesapal refund API.
    return transaction


@db_transaction.atomic
def flag_dispute(transaction, raised_by_user):
    task = transaction.task
    transaction.status = Transaction.Status.DISPUTED
    transaction.save(update_fields=["status", "updated_at"])

    task.status = Task.Status.DISPUTED
    task.save(update_fields=["status", "updated_at"])

    EscrowLedger.objects.create(
        transaction=transaction,
        action=EscrowLedger.Action.HOLD,
        amount=transaction.total_charged,
        note="Funds frozen - dispute raised",
    )

    send_notification(
        transaction.client,
        Notification.Type.TASK_DISPUTED,
        "Task dispute raised",
        "A dispute has been raised. Funds are frozen.",
        related_task=task,
    )
    send_notification(
        transaction.tasker,
        Notification.Type.TASK_DISPUTED,
        "Task dispute raised",
        "A dispute has been raised. Funds are frozen.",
        related_task=task,
    )
    send_mail(
        subject="Taskit dispute raised",
        message=(
            f"Dispute raised by {raised_by_user.email} for task "
            f"#{task.id}: {task.title}"
        ),
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=True,
    )
    return transaction
