from datetime import timedelta
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import PlatformFeeUsage, PlatformInvoice, Transaction, quantize_money

TRIAL_DAYS = 14
GRACE_PERIOD_DAYS = 3


def first_day_of_month(value):
    return value.date().replace(day=1)


def trial_ends_at(user):
    return user.date_joined + timedelta(days=TRIAL_DAYS)


def is_user_in_trial(user, at_time=None):
    return (at_time or timezone.now()) < trial_ends_at(user)


def track_platform_fee(transaction):
    tasker = transaction.tasker
    completed_at = transaction.released_at or timezone.now()
    trial_usage = completed_at < trial_ends_at(tasker)
    fee_amount = Decimal("0.00") if trial_usage else transaction.platform_fee

    usage, _ = PlatformFeeUsage.objects.get_or_create(
        transaction=transaction,
        defaults={
            "tasker": tasker,
            "task": transaction.task,
            "task_amount": transaction.agreed_amount,
            "fee_amount": quantize_money(fee_amount),
            "billing_month": first_day_of_month(completed_at),
            "is_trial_usage": trial_usage,
            "status": PlatformFeeUsage.Status.WAIVED if trial_usage else PlatformFeeUsage.Status.TRACKED,
        },
    )
    return usage


def generate_invoice_for_month(user, billing_month=None):
    billing_month = billing_month or first_day_of_month(timezone.now())
    usages = PlatformFeeUsage.objects.filter(
        tasker=user,
        billing_month=billing_month,
        status=PlatformFeeUsage.Status.TRACKED,
        is_trial_usage=False,
    )
    amount = usages.aggregate(total=Sum("fee_amount"))["total"] or Decimal("0.00")
    amount = quantize_money(amount)
    if amount <= 0:
        return None

    invoice, _ = PlatformInvoice.objects.get_or_create(
        tasker=user,
        billing_month=billing_month,
        defaults={
            "amount": amount,
            "due_date": timezone.now() + timedelta(days=GRACE_PERIOD_DAYS),
        },
    )
    if invoice.amount != amount and invoice.status == PlatformInvoice.Status.PENDING:
        invoice.amount = amount
        invoice.save(update_fields=["amount", "updated_at"])

    usages.update(status=PlatformFeeUsage.Status.INVOICED, invoice=invoice)
    return invoice


def overdue_balance(user):
    return (
        PlatformInvoice.objects.filter(
            tasker=user,
            status=PlatformInvoice.Status.PENDING,
            due_date__lt=timezone.now(),
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )


def has_overdue_invoice(user):
    return overdue_balance(user) > 0


def billing_summary(user):
    now = timezone.now()
    month = first_day_of_month(now)
    current_usages = PlatformFeeUsage.objects.filter(tasker=user, billing_month=month)
    billable_usages = current_usages.filter(
        is_trial_usage=False,
        status__in=[PlatformFeeUsage.Status.TRACKED, PlatformFeeUsage.Status.INVOICED],
    )
    trial_usages = current_usages.filter(is_trial_usage=True)
    pending_invoices = PlatformInvoice.objects.filter(
        tasker=user,
        status=PlatformInvoice.Status.PENDING,
    )

    current_due = billable_usages.aggregate(total=Sum("fee_amount"))["total"] or Decimal("0.00")
    trial_waived = trial_usages.aggregate(total=Sum("task_amount"))["total"] or Decimal("0.00")
    overdue = overdue_balance(user)

    return {
        "trial_ends_at": trial_ends_at(user),
        "is_trial_active": is_user_in_trial(user, now),
        "grace_period_days": GRACE_PERIOD_DAYS,
        "current_month": month,
        "current_month_due": str(quantize_money(current_due)),
        "trial_waived_task_volume": str(quantize_money(trial_waived)),
        "overdue_balance": str(quantize_money(overdue)),
        "can_bid": overdue <= 0,
        "tracked_tasks": [
            {
                "id": usage.id,
                "task_id": usage.task_id,
                "task_title": usage.task.title,
                "task_amount": str(usage.task_amount),
                "fee_amount": str(usage.fee_amount),
                "is_trial_usage": usage.is_trial_usage,
                "status": usage.status,
                "created_at": usage.created_at,
            }
            for usage in current_usages.select_related("task").order_by("-created_at")[:50]
        ],
        "pending_invoices": [
            {
                "id": invoice.id,
                "billing_month": invoice.billing_month,
                "amount": str(invoice.amount),
                "due_date": invoice.due_date,
                "is_overdue": invoice.is_overdue,
                "status": invoice.status,
            }
            for invoice in pending_invoices.order_by("-created_at")
        ],
    }
