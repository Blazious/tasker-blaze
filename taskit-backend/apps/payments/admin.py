from django.contrib import admin

from .models import DisputeNote, EscrowLedger, PlatformFeeUsage, PlatformInvoice, PlatformInvoicePayment, Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "client",
        "tasker",
        "agreed_amount",
        "platform_fee",
        "tasker_payout",
        "status",
        "paid_at",
    )
    list_filter = ("status",)
    search_fields = ("task__title", "client__email", "tasker__email")
    readonly_fields = ("created_at", "updated_at", "paid_at", "released_at")


@admin.register(EscrowLedger)
class EscrowLedgerAdmin(admin.ModelAdmin):
    list_display = ("transaction", "action", "amount", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("transaction__task__title", "note")
    readonly_fields = ("created_at",)


@admin.register(DisputeNote)
class DisputeNoteAdmin(admin.ModelAdmin):
    list_display = ("task", "raised_by", "reason", "created_at")
    list_filter = ("created_at",)
    search_fields = ("task__title", "raised_by__email", "reason", "details")
    readonly_fields = ("created_at",)


@admin.register(PlatformFeeUsage)
class PlatformFeeUsageAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "tasker",
        "task_amount",
        "fee_amount",
        "billing_month",
        "status",
        "is_trial_usage",
    )
    list_filter = ("status", "is_trial_usage", "billing_month", "created_at")
    search_fields = ("task__title", "tasker__email")
    readonly_fields = ("created_at",)


@admin.register(PlatformInvoice)
class PlatformInvoiceAdmin(admin.ModelAdmin):
    list_display = ("tasker", "billing_month", "amount", "status", "due_date", "paid_at")
    list_filter = ("status", "billing_month", "due_date")
    search_fields = ("tasker__email", "notes")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PlatformInvoicePayment)
class PlatformInvoicePaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "tasker", "amount", "provider", "status", "provider_invoice_id", "created_at")
    list_filter = ("provider", "status", "created_at")
    search_fields = ("api_ref", "provider_invoice_id", "checkout_id", "tasker__email")
    readonly_fields = ("created_at", "updated_at", "paid_at", "raw_response", "raw_callback")
