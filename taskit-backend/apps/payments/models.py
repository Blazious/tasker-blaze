from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.utils import timezone


MONEY_QUANTIZER = Decimal("0.01")
WHOLE_SHILLING_QUANTIZER = Decimal("1")
PLATFORM_FEE_RATE = Decimal("0.10")


def quantize_money(value):
    return Decimal(value).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def quantize_whole_shillings(value):
    return Decimal(value).quantize(WHOLE_SHILLING_QUANTIZER, rounding=ROUND_HALF_UP)


class Transaction(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        ESCROWED = "ESCROWED", "Escrowed"
        RELEASED = "RELEASED", "Released"
        REFUNDED = "REFUNDED", "Refunded"
        DISPUTED = "DISPUTED", "Disputed"

    task = models.OneToOneField(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="transaction",
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_transactions",
    )
    tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="earning_transactions",
    )
    agreed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tasker_payout = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_charged = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )
    pesapal_order_id = models.CharField(max_length=255, blank=True)
    pesapal_tracking_id = models.CharField(max_length=255, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)
    payment_provider = models.CharField(max_length=50, default="ECONFIRM")
    econfirm_transaction_id = models.CharField(max_length=255, blank=True)
    econfirm_checkout_request_id = models.CharField(max_length=255, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, blank=True)
    econfirm_confirmation_code = models.CharField(max_length=100, blank=True)
    buyer_confirmed_at = models.DateTimeField(null=True, blank=True)
    econfirm_webhook_received_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.platform_fee = quantize_money(self.agreed_amount * PLATFORM_FEE_RATE)
        self.tasker_payout = quantize_money(self.agreed_amount)
        self.total_charged = quantize_money(self.agreed_amount)
        super().save(*args, **kwargs)

    @classmethod
    def create_for_task(cls, task, bid):
        return cls.objects.create(
            task=task,
            client=task.client,
            tasker=bid.tasker,
            agreed_amount=bid.amount,
        )

    def __str__(self):
        return f"Transaction #{self.pk} for {self.task}"

    def has_confirmation_code(self):
        return bool(self.econfirm_confirmation_code)

    def can_release(self):
        return self.status == self.Status.ESCROWED and self.has_confirmation_code()


class EscrowLedger(models.Model):
    class Action(models.TextChoices):
        HOLD = "HOLD", "Hold"
        RELEASE = "RELEASE", "Release"
        REFUND = "REFUND", "Refund"
        FEE_COLLECTED = "FEE_COLLECTED", "Fee Collected"

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} KES {self.amount}"


class DisputeNote(models.Model):
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="dispute_notes",
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="raised_disputes",
    )
    reason = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispute on {self.task} by {self.raised_by}"


class PlatformFeeUsage(models.Model):
    class Status(models.TextChoices):
        TRACKED = "TRACKED", "Tracked"
        INVOICED = "INVOICED", "Invoiced"
        WAIVED = "WAIVED", "Waived"

    tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_fee_usages",
    )
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="platform_fee_usage",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="platform_fee_usages",
    )
    task_amount = models.DecimalField(max_digits=10, decimal_places=2)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    billing_month = models.DateField()
    is_trial_usage = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRACKED,
    )
    invoice = models.ForeignKey(
        "PlatformInvoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usages",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tasker} fee KES {self.fee_amount} for {self.task}"


class PlatformInvoice(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        WAIVED = "WAIVED", "Waived"
        CANCELLED = "CANCELLED", "Cancelled"

    tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_invoices",
    )
    billing_month = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    due_date = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("tasker", "billing_month")

    @property
    def is_overdue(self):
        return self.status == self.Status.PENDING and self.due_date < timezone.now()

    def __str__(self):
        return f"{self.tasker} invoice KES {self.amount} due {self.due_date:%Y-%m-%d}"


class PlatformInvoicePayment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"

    invoice = models.ForeignKey(
        PlatformInvoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_invoice_payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    provider = models.CharField(max_length=50, default="INTASEND")
    api_ref = models.CharField(max_length=120, unique=True)
    provider_invoice_id = models.CharField(max_length=120, blank=True)
    checkout_id = models.CharField(max_length=120, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    raw_response = models.JSONField(default=dict, blank=True)
    raw_callback = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider} payment {self.api_ref} for invoice #{self.invoice_id}"
