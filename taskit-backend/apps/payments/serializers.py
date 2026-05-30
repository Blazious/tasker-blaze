from rest_framework import serializers

from .models import DisputeNote, EscrowLedger, PlatformFeeUsage, PlatformInvoice, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "task",
            "task_title",
            "client",
            "tasker",
            "agreed_amount",
            "platform_fee",
            "tasker_payout",
            "total_charged",
            "status",
            "pesapal_order_id",
            "pesapal_tracking_id",
            "payment_method",
            "payment_provider",
            "econfirm_transaction_id",
            "econfirm_checkout_request_id",
            "mpesa_receipt_number",
            "paid_at",
            "released_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class EscrowLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscrowLedger
        fields = ("id", "transaction", "action", "amount", "note", "created_at")
        read_only_fields = fields


class DisputeNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeNote
        fields = ("id", "task", "raised_by", "reason", "details", "created_at")
        read_only_fields = ("id", "task", "raised_by", "created_at")


class DisputeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisputeNote
        fields = ("reason", "details")

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reason is required.")
        return value


class PlatformBillingUserSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    phone_number = serializers.CharField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    is_kyc_verified = serializers.BooleanField(read_only=True)


class AdminPlatformFeeUsageSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source="task.title", read_only=True)
    transaction_status = serializers.CharField(source="transaction.status", read_only=True)

    class Meta:
        model = PlatformFeeUsage
        fields = (
            "id",
            "task",
            "task_title",
            "transaction",
            "transaction_status",
            "task_amount",
            "fee_amount",
            "billing_month",
            "is_trial_usage",
            "status",
            "created_at",
        )
        read_only_fields = fields


class AdminPlatformInvoiceSerializer(serializers.ModelSerializer):
    tasker = PlatformBillingUserSummarySerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    latest_payment_status = serializers.SerializerMethodField()
    usages = AdminPlatformFeeUsageSerializer(many=True, read_only=True)

    class Meta:
        model = PlatformInvoice
        fields = (
            "id",
            "tasker",
            "billing_month",
            "amount",
            "status",
            "due_date",
            "is_overdue",
            "paid_at",
            "notes",
            "latest_payment_status",
            "usages",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "tasker",
            "billing_month",
            "amount",
            "due_date",
            "is_overdue",
            "paid_at",
            "latest_payment_status",
            "usages",
            "created_at",
            "updated_at",
        )

    def get_latest_payment_status(self, obj):
        payment = obj.payments.order_by("-created_at").first()
        return payment.status if payment else None

    def validate_status(self, value):
        if self.instance.status == PlatformInvoice.Status.PAID and value != PlatformInvoice.Status.PAID:
            raise serializers.ValidationError("Paid invoices cannot be changed from the admin billing queue.")
        if value == PlatformInvoice.Status.PAID and self.instance.status != PlatformInvoice.Status.PAID:
            raise serializers.ValidationError("Invoices are marked paid only by the payment provider callback.")
        return value
