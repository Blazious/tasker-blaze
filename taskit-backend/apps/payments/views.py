import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.models import Bid, Task

from .billing import billing_summary, generate_invoice_for_month
from .econfirm import EconfirmClient
from .escrow import (
    flag_dispute,
    hold_funds,
    econfirm_payload_is_funded,
    econfirm_payload_is_released,
    reconcile_transaction_from_econfirm_payload,
    release_funds,
    sync_funds_from_econfirm,
    sync_transaction_from_econfirm,
)
from .intasend import IntaSendClient, mark_invoice_payment_failed, mark_invoice_payment_paid
from .models import DisputeNote, PlatformFeeUsage, PlatformInvoice, PlatformInvoicePayment, Transaction
from .serializers import AdminPlatformInvoiceSerializer, DisputeCreateSerializer, TransactionSerializer

logger = logging.getLogger(__name__)


def _nested_dict(payload, key):
    value = payload.get(key) if isinstance(payload, dict) else None
    return value if isinstance(value, dict) else {}


def _first_payload_value(payload, *keys):
    if not isinstance(payload, dict):
        return ""
    containers = (payload, _nested_dict(payload, "data"), _nested_dict(payload, "callback"))
    for container in containers:
        for key in keys:
            value = container.get(key)
            if value not in (None, ""):
                return str(value)
    return ""


class PaymentsHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"app": "payments", "status": "ok"})


class InitiatePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(
            Task.objects.select_related("client", "assigned_tasker"),
            pk=task_id,
        )
        if task.client_id != request.user.id:
            raise PermissionDenied("Only the task client can initiate payment.")
        if task.status != Task.Status.ASSIGNED:
            raise ValidationError("Task must be assigned before payment is initiated.")

        bid = task.bids.filter(status=Bid.Status.ACCEPTED).select_related("tasker").first()
        if bid is None:
            raise ValidationError("Task must have an accepted bid before payment.")
        if bid.amount < 100:
            raise ValidationError(
                "eConfirm requires a minimum escrow amount of KES 100. "
                "Please adjust the accepted bid amount before initiating payment."
            )

        transaction, _ = Transaction.objects.get_or_create(
            task=task,
            defaults={
                "client": task.client,
                "tasker": bid.tasker,
                "agreed_amount": bid.amount,
            },
        )
        if transaction.status == Transaction.Status.PENDING_PAYMENT and transaction.agreed_amount != bid.amount:
            transaction.agreed_amount = bid.amount
            transaction.save(update_fields=["agreed_amount", "platform_fee", "tasker_payout", "total_charged", "updated_at"])

        econfirm = EconfirmClient()
        escrow_payload = econfirm.create_escrow(
            transaction=transaction,
            description=f"TaskiT payment for {task.title}",
        )
        stk_payload = econfirm.initiate_stk_push(transaction)
        payment_url = (
            stk_payload.get("checkout_url")
            or stk_payload.get("payment_url")
            or stk_payload.get("data", {}).get("checkout_url")
            or stk_payload.get("data", {}).get("payment_url")
            or escrow_payload.get("checkout_url")
            or escrow_payload.get("payment_url")
            or escrow_payload.get("data", {}).get("checkout_url")
            or escrow_payload.get("data", {}).get("payment_url")
            or ""
        )

        return Response(
            {
                "message": "eConfirm escrow created. Approve the M-Pesa prompt to fund escrow.",
                "payment_url": payment_url,
                "provider": "ECONFIRM",
                "econfirm_transaction_id": transaction.econfirm_transaction_id,
                "amount": f"KES {transaction.total_charged}",
                "breakdown": {
                    "task_amount": str(transaction.agreed_amount),
                    "platform_fee": str(transaction.platform_fee),
                    "platform_fee_note": "Tracked for post-paid billing, not charged upfront.",
                    "total": str(transaction.total_charged),
                },
            }
        )


class PesapalIPNCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        order_tracking_id = request.data.get("OrderTrackingId", "")
        merchant_reference = request.data.get("OrderMerchantReference", "")

        try:
            if order_tracking_id and merchant_reference:
                status_payload = PesapalClient().get_transaction_status(order_tracking_id)
                if status_payload.get("payment_status_description") == "Completed":
                    transaction = Transaction.objects.select_related("task").get(
                        id=merchant_reference
                    )
                    transaction.pesapal_order_id = order_tracking_id
                    transaction.pesapal_tracking_id = status_payload.get(
                        "confirmation_code",
                        "",
                    )
                    transaction.payment_method = status_payload.get(
                        "payment_method",
                        "",
                    )
                    transaction.save(
                        update_fields=[
                            "pesapal_order_id",
                            "pesapal_tracking_id",
                            "payment_method",
                            "updated_at",
                        ]
                    )
                    if transaction.status == Transaction.Status.PENDING_PAYMENT:
                        hold_funds(transaction)
        except Exception:
            logger.exception("Pesapal IPN processing failed")

        return Response(
            {
                "orderNotificationType": "IPNCHANGE",
                "orderTrackingId": order_tracking_id,
                "orderMerchantReference": merchant_reference,
                "status": 200,
            },
            status=status.HTTP_200_OK,
        )


class EconfirmCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data
        event_type = _first_payload_value(payload, "event", "event_type", "type")
        econfirm_transaction_id = _first_payload_value(
            payload,
            "transaction_id",
            "econfirm_transaction_id",
            "escrow_id",
            "id",
        )
        econfirm_status = _first_payload_value(
            payload,
            "status",
            "state",
            "payment_status",
            "escrow_status",
        )
        internal_transaction_id = (
            payload.get("metadata", {}).get("transaction_id")
            if isinstance(payload.get("metadata"), dict)
            else payload.get("transaction_reference", "")
        )

        try:
            transaction = None
            if econfirm_transaction_id:
                transaction = Transaction.objects.select_related("task").filter(
                    Q(econfirm_transaction_id=econfirm_transaction_id)
                    | Q(econfirm_checkout_request_id=econfirm_transaction_id)
                ).first()
            if transaction is None and internal_transaction_id:
                transaction = Transaction.objects.select_related("task").filter(
                    id=internal_transaction_id
                ).first()

            if transaction is None:
                return Response({"error": "Transaction not found"}, status=404)

            mpesa_receipt = _first_payload_value(
                payload,
                "confirmation_code",
                "mpesa_confirmation_code",
                "mpesa_receipt",
                "mpesa_receipt_number",
                "receipt",
                "provider_reference",
                "payment_reference",
            )
            payment_method = _first_payload_value(payload, "payment_method", "method")
            if mpesa_receipt:
                transaction.mpesa_receipt_number = mpesa_receipt
            if payment_method:
                transaction.payment_method = payment_method
            transaction.payment_provider = "ECONFIRM"
            transaction.save(
                update_fields=[
                    "mpesa_receipt_number",
                    "payment_method",
                    "payment_provider",
                    "updated_at",
                ]
            )

            if econfirm_payload_is_funded(payload) or econfirm_payload_is_released(payload):
                reconcile_transaction_from_econfirm_payload(transaction, payload)
            elif event_type in {"payment.failed", "escrow.failed"}:
                transaction.status = Transaction.Status.PENDING_PAYMENT
                transaction.save(update_fields=["status", "updated_at"])
            elif event_type == "funds.refunded" or econfirm_status == "refunded":
                transaction.status = Transaction.Status.REFUNDED
                transaction.save(update_fields=["status", "updated_at"])
        except Exception:
            logger.exception("eConfirm callback processing failed")
            return Response({"status": "accepted"}, status=status.HTTP_200_OK)

        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class PaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        transaction = get_object_or_404(
            Transaction.objects.select_related("task"),
            task_id=task_id,
        )
        task = transaction.task
        if request.user.id not in {transaction.client_id, transaction.tasker_id}:
            raise PermissionDenied("You cannot view this payment status.")

        external_status, synced = sync_transaction_from_econfirm(transaction)
        if synced:
            transaction.refresh_from_db()
            task.refresh_from_db()

        return Response(
            {
                "status": transaction.status,
                "paid_at": transaction.paid_at,
                "amount": str(transaction.total_charged),
                "task_status": task.status,
                "tasker_completed_at": task.tasker_completed_at,
                "provider": transaction.payment_provider,
                "external_status": external_status,
                "synced": synced,
            }
        )


class ConfirmEscrowFundedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        transaction = get_object_or_404(
            Transaction.objects.select_related("task"),
            task_id=task_id,
        )
        if transaction.client_id != request.user.id:
            raise PermissionDenied("Only the task client can confirm escrow funding.")
        if transaction.status != Transaction.Status.PENDING_PAYMENT:
            return Response({"message": "Escrow is already synced.", "status": transaction.status})
        if not transaction.econfirm_transaction_id:
            raise ValidationError("No eConfirm transaction exists for this task yet.")

        external_status, synced = sync_funds_from_econfirm(transaction)
        if not synced:
            if not settings.DEBUG:
                raise ValidationError(
                    {
                        "message": "eConfirm has not confirmed escrow funding yet. Tap Check again after the STK payment completes.",
                        "external_status": external_status,
                    }
                )
            hold_funds(transaction)
        transaction.refresh_from_db()
        task = transaction.task
        return Response(
            {
                "message": "Escrow funding confirmed. You can now release after the task is complete.",
                "status": transaction.status,
                "task_status": task.status,
                "external_status": external_status,
            }
        )


class ReleasePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        transaction = get_object_or_404(
            Transaction.objects.select_related("task"),
            task_id=task_id,
        )
        if transaction.client_id != request.user.id:
            raise PermissionDenied("Only the task client can release payment.")
        if not transaction.task.tasker_completed_at:
            raise ValidationError("The tasker must mark the task complete before funds can be released.")

        if transaction.status in {
            Transaction.Status.PENDING_PAYMENT,
            Transaction.Status.ESCROWED,
        }:
            external_status, synced = sync_transaction_from_econfirm(transaction)
            if synced:
                transaction.refresh_from_db()
                if transaction.status == Transaction.Status.RELEASED:
                    return Response({"message": "Payment release synced. Reviews are now open."})

        if transaction.status != Transaction.Status.ESCROWED:
            raise ValidationError("Escrow is not funded yet, so funds cannot be released.")

        confirmation_code = request.data.get("confirmation_code") or request.data.get("mpesa_receipt_number") or ""
        release_funds(transaction, confirmation_code=confirmation_code)
        return Response({"message": "Payment released. Great job!"})


class DisputePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        transaction = get_object_or_404(
            Transaction.objects.select_related("task"),
            task_id=task_id,
        )
        if request.user.id not in {transaction.client_id, transaction.tasker_id}:
            raise PermissionDenied("Only the client or assigned tasker can raise a dispute.")

        serializer = DisputeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DisputeNote.objects.create(
            task=transaction.task,
            raised_by=request.user,
            **serializer.validated_data,
        )
        flag_dispute(transaction, request.user)
        return Response(
            {"message": "Dispute flagged. Our team will review within 24 hours."}
        )


class MyEarningsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = Transaction.objects.filter(tasker=request.user).select_related(
            "task",
            "client",
        )
        total_earned = (
            transactions.filter(status=Transaction.Status.RELEASED).aggregate(
                total=Sum("tasker_payout")
            )["total"]
            or 0
        )
        pending_payout = (
            transactions.filter(status=Transaction.Status.ESCROWED).aggregate(
                total=Sum("tasker_payout")
            )["total"]
            or 0
        )
        recent = transactions.order_by("-created_at")[:20]

        return Response(
            {
                "total_earned": str(total_earned),
                "pending_payout": str(pending_payout),
                "total_tasks": transactions.filter(status=Transaction.Status.RELEASED).count(),
                "transactions": [
                    {
                        "task_title": transaction.task.title,
                        "client_name": transaction.client.full_name,
                        "agreed_amount": str(transaction.agreed_amount),
                        "platform_fee": str(transaction.platform_fee),
                        "tasker_payout": str(transaction.tasker_payout),
                        "status": transaction.status,
                        "paid_at": transaction.paid_at,
                        "released_at": transaction.released_at,
                        "created_at": transaction.created_at,
                    }
                    for transaction in recent
                ],
            }
        )


class MySpendingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transactions = (
            Transaction.objects.filter(client=request.user)
            .select_related("task", "tasker")
            .order_by("-created_at")
        )
        total_spent = (
            transactions.filter(status=Transaction.Status.RELEASED).aggregate(
                total=Sum("total_charged")
            )["total"]
            or 0
        )

        return Response(
            {
                "total_spent": str(total_spent),
                "transactions": TransactionSerializer(transactions, many=True).data,
            }
        )


class PlatformBillingSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(billing_summary(request.user))

    def post(self, request):
        invoice = generate_invoice_for_month(request.user)
        summary = billing_summary(request.user)
        summary["generated_invoice_id"] = invoice.id if invoice else None
        return Response(summary)


class AdminPlatformInvoiceListView(generics.ListAPIView):
    serializer_class = AdminPlatformInvoiceSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = (
            PlatformInvoice.objects.select_related("tasker")
            .prefetch_related("payments", "usages", "usages__task", "usages__transaction")
        )
        status_filter = self.request.query_params.get("status")
        overdue_filter = self.request.query_params.get("overdue")

        if status_filter and status_filter != "ALL":
            queryset = queryset.filter(status=status_filter)
        if overdue_filter == "true":
            queryset = queryset.filter(
                status=PlatformInvoice.Status.PENDING,
                due_date__lt=timezone.now(),
            )

        return queryset


class AdminPlatformInvoiceDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminPlatformInvoiceSerializer
    permission_classes = [IsAdminUser]
    queryset = (
        PlatformInvoice.objects.select_related("tasker")
        .prefetch_related("payments", "usages", "usages__task", "usages__transaction")
    )
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        invoice = serializer.save()
        if invoice.status == PlatformInvoice.Status.WAIVED:
            invoice.usages.update(status=PlatformFeeUsage.Status.WAIVED)
        elif invoice.status == PlatformInvoice.Status.PENDING:
            invoice.usages.update(status=PlatformFeeUsage.Status.INVOICED)
        elif invoice.status == PlatformInvoice.Status.CANCELLED:
            invoice.usages.update(status=PlatformFeeUsage.Status.TRACKED, invoice=None)


class TestPlatformInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.ENABLE_TEST_BILLING_TOOLS:
            raise PermissionDenied("Test billing tools are disabled.")

        amount = Decimal(str(request.data.get("amount", "70.00")))
        if amount <= 0 or amount > Decimal("70.00"):
            raise ValidationError("Test invoice amount must be between KES 1 and KES 70.")

        month = timezone.now().date().replace(day=1)
        invoice, _ = PlatformInvoice.objects.update_or_create(
            tasker=request.user,
            billing_month=month,
            defaults={
                "amount": amount,
                "status": PlatformInvoice.Status.PENDING,
                "due_date": timezone.now() + timedelta(days=3),
                "notes": "Manual test invoice for IntaSend billing",
            },
        )
        summary = billing_summary(request.user)
        summary["generated_invoice_id"] = invoice.id
        summary["test_invoice_id"] = invoice.id
        return Response(summary)


class PayPlatformInvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, invoice_id):
        invoice = get_object_or_404(PlatformInvoice, pk=invoice_id, tasker=request.user)
        if invoice.status == PlatformInvoice.Status.PAID:
            return Response({"message": "Invoice is already paid.", "status": invoice.status})
        if invoice.status != PlatformInvoice.Status.PENDING:
            raise ValidationError("Only pending invoices can be paid.")

        phone_number = request.data.get("phone_number") or request.user.phone_number
        payment = IntaSendClient().send_invoice_stk_push(invoice, phone_number)
        return Response(
            {
                "message": "STK push sent. Enter your M-Pesa PIN to pay the invoice.",
                "payment_id": payment.id,
                "invoice_id": invoice.id,
                "status": payment.status,
                "provider_invoice_id": payment.provider_invoice_id,
            }
        )


class PlatformInvoicePaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, invoice_id):
        invoice = get_object_or_404(PlatformInvoice, pk=invoice_id, tasker=request.user)
        payment = invoice.payments.order_by("-created_at").first()
        if payment is None:
            return Response({"invoice_status": invoice.status, "payment_status": None})

        if payment.status in (
            PlatformInvoicePayment.Status.PENDING,
            PlatformInvoicePayment.Status.PROCESSING,
        ):
            status_payload = IntaSendClient().check_payment_status(payment)
            state = str(status_payload.get("state") or status_payload.get("status") or "").upper()
            if state == "COMPLETE":
                mark_invoice_payment_paid(payment, status_payload)
                invoice.refresh_from_db()
            elif state == "FAILED":
                mark_invoice_payment_failed(
                    payment,
                    status_payload,
                    status_payload.get("failed_reason", ""),
                )

        payment.refresh_from_db()
        return Response(
            {
                "invoice_status": invoice.status,
                "payment_status": payment.status,
                "payment_id": payment.id,
                "provider_invoice_id": payment.provider_invoice_id,
                "paid_at": payment.paid_at,
            }
        )


class IntaSendInvoiceCallbackView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.data
        expected_challenge = settings.INTASEND_WEBHOOK_CHALLENGE
        if expected_challenge and payload.get("challenge") != expected_challenge:
            raise PermissionDenied("Invalid IntaSend webhook challenge.")

        api_ref = payload.get("api_ref", "")
        payment = PlatformInvoicePayment.objects.select_related("invoice").filter(
            api_ref=api_ref,
        ).first()
        if payment is None:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        provider_invoice_id = payload.get("invoice_id")
        if provider_invoice_id and not payment.provider_invoice_id:
            payment.provider_invoice_id = provider_invoice_id

        state = str(payload.get("state", "")).upper()
        if state == "COMPLETE":
            mark_invoice_payment_paid(payment, payload)
        elif state == "FAILED":
            mark_invoice_payment_failed(
                payment,
                payload,
                payload.get("failed_reason", ""),
            )
        elif state in {"PENDING", "PROCESSING"}:
            payment.status = PlatformInvoicePayment.Status.PROCESSING
            payment.raw_callback = payload
            payment.save(update_fields=["provider_invoice_id", "status", "raw_callback", "updated_at"])

        return Response({"status": "ok"})


class MockConfirmPaymentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, transaction_id):
        if not settings.DEBUG or not (settings.ECONFIRM_MOCK or settings.PESAPAL_MOCK):
            raise PermissionDenied("Mock payments are disabled.")

        transaction = get_object_or_404(Transaction, pk=transaction_id)
        hold_funds(transaction)
        return Response({"message": "Mock payment confirmed. Funds escrowed."})
