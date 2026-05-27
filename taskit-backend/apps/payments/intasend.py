import logging

import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .econfirm import sanitize_for_logs, validate_kenyan_mobile
from .models import PlatformInvoice, PlatformInvoicePayment

logger = logging.getLogger(__name__)


class IntaSendClient:
    def __init__(self):
        self.secret_key = settings.INTASEND_SECRET_KEY
        self.base_url = settings.INTASEND_BASE_URL.rstrip("/")

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _post(self, path, payload, error_message):
        if not self.secret_key:
            raise ValidationError("IntaSend is not configured. Add INTASEND_SECRET_KEY.")

        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception(
                "%s: %s",
                error_message,
                sanitize_for_logs(response.text[:500]),
            )
            raise ValidationError(error_message) from exc
        return response.json()

    def send_invoice_stk_push(self, invoice, phone_number):
        normalized_phone = validate_kenyan_mobile(phone_number, "Your profile")
        api_ref = f"TASKIT-INVOICE-{invoice.id}-{timezone.now():%Y%m%d%H%M%S}"
        payment = PlatformInvoicePayment.objects.create(
            invoice=invoice,
            tasker=invoice.tasker,
            amount=invoice.amount,
            api_ref=api_ref,
            phone_number=normalized_phone,
        )
        payload = {
            "amount": str(invoice.amount),
            "phone_number": normalized_phone,
            "api_ref": api_ref,
            "mobile_tarrif": "CUSTOMER-PAYS",
        }
        response = self._post(
            "/payment/mpesa-stk-push/",
            payload,
            "Could not start IntaSend invoice STK push.",
        )
        payment.provider_invoice_id = str(response.get("invoice_id") or response.get("id") or "")
        payment.checkout_id = str(response.get("checkout_id") or "")
        payment.status = PlatformInvoicePayment.Status.PROCESSING
        payment.raw_response = response
        payment.save(
            update_fields=[
                "provider_invoice_id",
                "checkout_id",
                "status",
                "raw_response",
                "updated_at",
            ]
        )
        return payment

    def check_payment_status(self, payment):
        if not payment.provider_invoice_id:
            raise ValidationError("IntaSend invoice reference is missing.")
        return self._post(
            "/payment/status/",
            {
                "invoice_id": payment.provider_invoice_id,
                **({"checkout_id": payment.checkout_id} if payment.checkout_id else {}),
            },
            "Could not check IntaSend invoice payment status.",
        )


def mark_invoice_payment_paid(payment, payload=None):
    now = timezone.now()
    payment.status = PlatformInvoicePayment.Status.PAID
    payment.paid_at = now
    if payload is not None:
        payment.raw_callback = payload
    payment.save(update_fields=["status", "paid_at", "raw_callback", "updated_at"])

    invoice = payment.invoice
    invoice.status = PlatformInvoice.Status.PAID
    invoice.paid_at = now
    invoice.save(update_fields=["status", "paid_at", "updated_at"])
    invoice.usages.update(status="INVOICED")
    return payment


def mark_invoice_payment_failed(payment, payload=None, reason=""):
    payment.status = PlatformInvoicePayment.Status.FAILED
    payment.failure_reason = reason
    if payload is not None:
        payment.raw_callback = payload
    payment.save(update_fields=["status", "failure_reason", "raw_callback", "updated_at"])
    return payment
