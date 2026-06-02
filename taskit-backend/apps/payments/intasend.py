import logging
from decimal import Decimal
from json import JSONDecodeError

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

        logger.warning("IntaSend request %s payload=%s", path, sanitize_for_logs(payload))
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            details = self._error_details(response)
            logger.exception(
                "%s: %s",
                error_message,
                details,
            )
            raise ValidationError(f"{error_message}: {details}") from exc
        data = response.json()
        logger.warning("IntaSend response %s data=%s", path, sanitize_for_logs(data))
        return data

    def _error_details(self, response):
        try:
            data = response.json()
        except (ValueError, JSONDecodeError):
            text = response.text[:500].strip()
            return sanitize_for_logs(text) or f"HTTP {response.status_code}"

        data = sanitize_for_logs(data)
        if isinstance(data, dict):
            for key in ("detail", "message", "error", "errors", "non_field_errors"):
                if data.get(key):
                    return data[key]
        return data or f"HTTP {response.status_code}"

    def _mpesa_amount(self, amount):
        value = Decimal(str(amount))
        whole_value = value.to_integral_value()
        if value != whole_value:
            raise ValidationError(
                "Platform invoice amount must be a whole KES amount before M-Pesa payment can start."
            )
        if whole_value <= 0:
            raise ValidationError("Platform invoice amount must be greater than zero.")
        return str(int(whole_value))

    def send_invoice_stk_push(self, invoice, phone_number):
        normalized_phone = validate_kenyan_mobile(phone_number, "Your profile")
        amount = self._mpesa_amount(invoice.amount)
        api_ref = f"TASKIT-INVOICE-{invoice.id}-{timezone.now():%Y%m%d%H%M%S}"
        name_parts = (invoice.tasker.full_name or "").strip().split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        payment = PlatformInvoicePayment.objects.create(
            invoice=invoice,
            tasker=invoice.tasker,
            amount=invoice.amount,
            api_ref=api_ref,
            phone_number=normalized_phone,
        )
        payload = {
            "amount": amount,
            "phone_number": normalized_phone,
            "email": invoice.tasker.email,
            "first_name": first_name,
            "last_name": last_name,
            "currency": "KES",
            "api_ref": api_ref,
            "narrative": f"TaskiT platform invoice #{invoice.id}",
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
