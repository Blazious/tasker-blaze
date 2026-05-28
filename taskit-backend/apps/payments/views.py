import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.models import Bid, Task

from .billing import billing_summary, generate_invoice_for_month, track_platform_fee
from .econfirm import EconfirmClient
from .escrow import flag_dispute, hold_funds, release_funds
from .intasend import IntaSendClient, mark_invoice_payment_failed, mark_invoice_payment_paid
from .models import DisputeNote, EscrowLedger, PlatformInvoice, PlatformInvoicePayment, Transaction
from .serializers import DisputeCreateSerializer, TransactionSerializer

logger = logging.getLogger(__name__)


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
        event_type = request.data.get("event", "")
        econfirm_transaction_id = (
            request.data.get("transaction_id")
            or request.data.get("econfirm_transaction_id")
            or request.data.get("id")
            or request.data.get("data", {}).get("id")
            or ""
        )
        econfirm_status = (
            request.data.get("status")
            or request.data.get("data", {}).get("status")
            or ""
        )
        internal_transaction_id = (
            request.data.get("metadata", {}).get("transaction_id")
            if isinstance(request.data.get("metadata"), dict)
            else request.data.get("transaction_reference", "")
        )

        try:
            transaction = None
            if econfirm_transaction_id:
                transaction = Transaction.objects.select_related("task").filter(
                    econfirm_transaction_id=econfirm_transaction_id
                ).first()
            if transaction is None and internal_transaction_id:
                transaction = Transaction.objects.select_related("task").filter(
                    id=internal_transaction_id
                ).first()

            if transaction is None:
                return Response({"error": "Transaction not found"}, status=404)

            mpesa_receipt = request.data.get("mpesa_receipt") or request.data.get("mpesa_receipt_number") or ""
            payment_method = request.data.get("payment_method") or request.data.get("data", {}).get("payment_method") or ""
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

            if event_type in {"payment.success", "escrow.funded", "funds.held"} or econfirm_status in {"funded", "in_progress"}:
                if transaction.status == Transaction.Status.PENDING_PAYMENT:
                    hold_funds(transaction)
            elif event_type in {"payment.failed", "escrow.failed"}:
                transaction.status = Transaction.Status.PENDING_PAYMENT
                transaction.save(update_fields=["status", "updated_at"])
            elif event_type == "funds.refunded" or econfirm_status == "refunded":
                transaction.status = Transaction.Status.REFUNDED
                transaction.save(update_fields=["status", "updated_at"])
            elif event_type == "funds.released" or econfirm_status in {"complete", "completed"}:
                transaction.status = Transaction.Status.RELEASED
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

        external_status = None
        if transaction.econfirm_transaction_id and transaction.status == Transaction.Status.PENDING_PAYMENT:
            external_status = EconfirmClient().check_transaction_status(
                transaction.econfirm_transaction_id
            )
            external_data = external_status.get("data", external_status) if external_status else {}
            external_state = str(external_data.get("status", "")).lower()
            if external_state in {"funded", "in_progress", "held", "escrowed"}:
                hold_funds(transaction)
                transaction.refresh_from_db()
                task.refresh_from_db()

        return Response(
            {
                "status": transaction.status,
                "paid_at": transaction.paid_at,
                "amount": str(transaction.total_charged),
                "task_status": task.status,
                "provider": transaction.payment_provider,
                "external_status": external_status,
            }
        )


class ConfirmEscrowFundedView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        if not settings.DEBUG:
            raise PermissionDenied("Manual escrow confirmation is only available in local development.")

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

        hold_funds(transaction)
        return Response(
            {
                "message": "Escrow funding confirmed. You can now release after the task is complete.",
                "status": Transaction.Status.ESCROWED,
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

        if transaction.status == Transaction.Status.PENDING_PAYMENT and transaction.econfirm_transaction_id:
            external_status = EconfirmClient().check_transaction_status(
                transaction.econfirm_transaction_id
            )
            external_data = external_status.get("data", external_status) if external_status else {}
            external_state = str(external_data.get("status", "")).lower()
            external_event = str(external_data.get("event", external_status.get("event", "") if external_status else "")).lower()
            if external_state in {"funded", "in_progress", "held", "escrowed"} or external_event in {
                "payment.success",
                "escrow.funded",
                "funds.held",
            }:
                hold_funds(transaction)
                transaction.refresh_from_db()
            elif external_state in {"complete", "completed", "released"} or external_event in {
                "funds.released",
                "escrow.released",
            }:
                now = timezone.now()
                transaction.status = Transaction.Status.RELEASED
                transaction.released_at = now
                transaction.save(update_fields=["status", "released_at", "updated_at"])
                task = transaction.task
                task.status = Task.Status.COMPLETED
                task.completed_at = now
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
                return Response({"message": "Payment release synced. Reviews are now open."})

        if transaction.status != Transaction.Status.ESCROWED:
            raise ValidationError("Escrow is not funded yet, so funds cannot be released.")

        release_funds(transaction)
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
