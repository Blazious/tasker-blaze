import logging
import re

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

KENYAN_MOBILE_PATTERN = re.compile(r"^254[17]\d{8}$")


def normalize_kenyan_phone(phone_number):
    digits = "".join(char for char in str(phone_number) if char.isdigit())
    if digits.startswith("2540") and len(digits) == 13:
        digits = f"254{digits[4:]}"
    if digits.startswith("0") and len(digits) == 10:
        return f"254{digits[1:]}"
    if digits.startswith("7") and len(digits) == 9:
        return f"254{digits}"
    if digits.startswith("1") and len(digits) == 9:
        return f"254{digits}"
    if digits.startswith("254") and len(digits) == 12:
        return digits
    return digits


def validate_kenyan_mobile(phone_number, label):
    normalized = normalize_kenyan_phone(phone_number)
    if not normalized:
        raise ValidationError(f"{label} needs a phone number before M-Pesa payment can start.")
    if not KENYAN_MOBILE_PATTERN.match(normalized):
        raise ValidationError(
            f"{label} phone number must be a valid Kenyan mobile number like 07XXXXXXXX or 01XXXXXXXX."
        )
    return normalized


class EconfirmClient:
    def __init__(self):
        self.api_key = settings.ECONFIRM_API_KEY
        self.base_url = settings.ECONFIRM_BASE_URL.rstrip("/")
        self.mock = settings.ECONFIRM_MOCK

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_escrow(self, transaction, description):
        if not self.api_key:
            raise ValidationError("ECONFIRM_API_KEY is missing. Add your live eConfirm API key to .env.")

        if self.mock:
            mock_checkout_url = f"http://localhost:8000/api/v1/payments/mock-confirm/{transaction.id}/"
            external_id = f"mock-econfirm-{transaction.id}"
            transaction.econfirm_transaction_id = external_id
            transaction.econfirm_checkout_request_id = f"mock-checkout-{transaction.id}"
            transaction.payment_provider = "ECONFIRM"
            transaction.save(
                update_fields=[
                    "econfirm_transaction_id",
                    "econfirm_checkout_request_id",
                    "payment_provider",
                    "updated_at",
                ]
            )
            logger.info("MOCK: eConfirm escrow created for transaction %s", transaction.id)
            return {
                "success": True,
                "data": {
                    "id": external_id,
                    "status": "pending",
                    "amount": float(transaction.agreed_amount),
                    "currency": "KES",
                    "checkout_url": mock_checkout_url,
                    "integration": {
                        "api_account_email_verified": True,
                        "max_principal_kes": 500000,
                    },
                },
            }

        buyer_phone = validate_kenyan_mobile(transaction.client.phone_number, "Your profile")
        seller_phone = validate_kenyan_mobile(transaction.tasker.phone_number, "The accepted tasker profile")

        # eConfirm v1 creates a principal escrow amount. TaskiT tracks the
        # platform fee post-paid, so the client funds only the agreed task amount.
        payload = {
            "buyer_email": transaction.client.email,
            "seller_email": transaction.tasker.email,
            "buyer_phone": buyer_phone,
            "seller_phone": seller_phone,
            "receiver_phone": seller_phone,
            "recipient_phone": seller_phone,
            "amount": float(transaction.agreed_amount),
            "currency": "KES",
            "description": description[:100],
            "terms": (
                f"TaskiT task #{transaction.task_id}. Funds release after client confirms task completion. "
                f"TaskiT post-paid platform fee tracked separately: KES {transaction.platform_fee}."
            ),
        }
        response = self._post("/transactions", payload, "Failed to create eConfirm escrow")
        data = response.get("data", response)

        transaction.econfirm_transaction_id = data.get("id", "")
        transaction.econfirm_checkout_request_id = data.get("checkout_request_id", "")
        transaction.payment_provider = "ECONFIRM"
        transaction.save(
            update_fields=[
                "econfirm_transaction_id",
                "econfirm_checkout_request_id",
                "payment_provider",
                "updated_at",
            ]
        )
        return data

    def initiate_stk_push(self, transaction):
        if self.mock:
            logger.info("MOCK: eConfirm STK push skipped for transaction %s", transaction.id)
            return {
                "success": True,
                "status": "mocked",
                "checkout_url": f"http://localhost:8000/api/v1/payments/mock-confirm/{transaction.id}/",
                "message": "Mock eConfirm payment ready.",
            }

        payload = {
            "transaction_id": transaction.econfirm_transaction_id,
            "payer_phone": validate_kenyan_mobile(transaction.client.phone_number, "Your profile"),
        }
        return self._post("/payments/stk-push", payload, "Failed to initiate eConfirm STK push")

    def check_transaction_status(self, econfirm_transaction_id):
        if self.mock:
            return {"status": "HELD", "event": "payment.success"}
        try:
            response = requests.get(
                f"{self.base_url}/transactions/{econfirm_transaction_id}",
                headers=self._headers(),
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            logger.exception("eConfirm status check failed")
            return None

    def release_funds(self, transaction):
        if self.mock:
            logger.info("MOCK: eConfirm release skipped for transaction %s", transaction.id)
            return {"status": "released"}

        payload = {
            "confirmation_code": f"TASKIT-{transaction.task_id}-{transaction.id}",
            "notes": (
                "Client confirmed completion in TaskiT. "
                "eConfirm releases to the seller configured on the escrow transaction."
            ),
        }
        return self._post(
            f"/transactions/{transaction.econfirm_transaction_id}/release",
            payload,
            "Failed to release eConfirm funds",
        )

    def refund_funds(self, transaction, reason):
        if self.mock:
            logger.info("MOCK: eConfirm refund skipped for transaction %s", transaction.id)
            return {"status": "refunded"}

        raise ValidationError(
            "eConfirm public API documentation does not expose a refund endpoint. "
            "Handle refunds from the eConfirm dashboard/support flow."
        )

    def _post(self, path, payload, error_message):
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            logger.exception("eConfirm API error on %s", path)
            response = getattr(exc, "response", None)
            details = ""
            if response is not None:
                details = f" - {response.text[:500]}"
            raise ValidationError(f"{error_message}: {exc}{details}") from exc
