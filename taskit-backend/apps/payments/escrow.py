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


FUNDED_STATES = {
    "funded",
    "in_progress",
    "held",
    "escrowed",
    "paid",
    "success",
    "successful",
}
FUNDED_EVENTS = {
    "payment.success",
    "escrow.funded",
    "funds.held",
    "payment_success",
    "payment_successful",
}
RELEASED_STATES = {
    "complete",
    "completed",
    "released",
    "release",
}
RELEASED_EVENTS = {
    "funds.released",
    "escrow.released",
    "funds_released",
    "escrow_released",
}


def _collect_external_values(payload, keys):
    values = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys and value is not None:
                values.append(str(value).lower())
            values.extend(_collect_external_values(value, keys))
    elif isinstance(payload, list):
        for item in payload:
            values.extend(_collect_external_values(item, keys))
    return values


def _normalize_external_value(value):
    return str(value).lower().replace("-", "_").replace(" ", "_")


def econfirm_payload_is_funded(payload):
    status_values = _collect_external_values(
        payload,
        {"status", "state", "payment_status", "transaction_status"},
    )
    event_values = _collect_external_values(payload, {"event", "event_type", "type"})
    normalized_statuses = [_normalize_external_value(value) for value in status_values]
    normalized_events = [_normalize_external_value(value) for value in event_values]
    return any(
        value in FUNDED_STATES
        or "funded" in value
        or "funds_held" in value
        or "held" == value
        or "held_in_escrow" in value
        or "escrowed" in value
        or "payment_success" in value
        for value in normalized_statuses
    ) or any(
        value in FUNDED_EVENTS
        or "funded" in value
        or "funds_held" in value
        or "payment_success" in value
        for value in normalized_events
    )


def econfirm_payload_is_released(payload):
    status_values = _collect_external_values(
        payload,
        {"status", "state", "payment_status", "transaction_status"},
    )
    event_values = _collect_external_values(payload, {"event", "event_type", "type"})
    normalized_statuses = [_normalize_external_value(value) for value in status_values]
    normalized_events = [_normalize_external_value(value) for value in event_values]
    return any(
        value in RELEASED_STATES
        or "released" in value
        or "funds_released" in value
        or "escrow_released" in value
        for value in normalized_statuses
    ) or any(
        value in RELEASED_EVENTS
        or "released" in value
        or "funds_released" in value
        or "escrow_released" in value
        for value in normalized_events
    )


def sync_transaction_from_econfirm(transaction):
    if (
        not transaction.econfirm_transaction_id
        or transaction.status not in {Transaction.Status.PENDING_PAYMENT, Transaction.Status.ESCROWED}
    ):
        return None, False

    external_status = EconfirmClient().check_transaction_status(
        transaction.econfirm_transaction_id
    )
    if external_status and econfirm_payload_is_released(external_status):
        mark_funds_released_from_econfirm(transaction, external_status)
        transaction.refresh_from_db()
        return external_status, True
    if (
        transaction.status == Transaction.Status.PENDING_PAYMENT
        and external_status
        and econfirm_payload_is_funded(external_status)
    ):
        hold_funds(transaction)
        transaction.refresh_from_db()
        return external_status, True
    return external_status, False


def sync_funds_from_econfirm(transaction):
    external_status, synced = sync_transaction_from_econfirm(transaction)
    transaction.refresh_from_db()
    return external_status, synced and transaction.status == Transaction.Status.ESCROWED


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
def mark_funds_released_from_econfirm(transaction, payload=None):
    if transaction.status == Transaction.Status.RELEASED:
        track_platform_fee(transaction)
        return transaction

    now = timezone.now()
    task = transaction.task

    transaction.status = Transaction.Status.RELEASED
    transaction.released_at = transaction.released_at or now
    transaction.save(update_fields=["status", "released_at", "updated_at"])

    task.status = Task.Status.COMPLETED
    task.completed_at = task.completed_at or now
    task.save(update_fields=["status", "completed_at", "updated_at"])

    EscrowLedger.objects.get_or_create(
        transaction=transaction,
        action=EscrowLedger.Action.RELEASE,
        defaults={
            "amount": transaction.tasker_payout,
            "note": "Tasker payout synced from eConfirm",
        },
    )
    track_platform_fee(transaction)

    send_notification(
        transaction.tasker,
        Notification.Type.TASK_COMPLETED,
        "Payout released",
        f"KES {transaction.tasker_payout} has been released. Reviews are now open.",
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
