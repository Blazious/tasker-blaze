from rest_framework import serializers

from .models import DisputeNote, EscrowLedger, Transaction


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
