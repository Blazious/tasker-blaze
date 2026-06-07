import logging
import re
from json import JSONDecodeError

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

KENYAN_MOBILE_PATTERN = re.compile(r"^254[17]\d{8}$")


def mask_value(value):
    text = str(value)
    if not text:
        return text
    if "@" in text:
        name, _, domain = text.partition("@")
        return f"{name[:2]}***@{domain}"
    digits = "".join(char for char in text if char.isdigit())
    if len(digits) >= 9:
        return f"{digits[:5]}***{digits[-3:]}"
    return "***"


def sanitize_for_logs(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_lower = key.lower()
            if any(marker in key_lower for marker in ("phone", "email", "msisdn", "payer", "buyer", "seller", "receiver", "recipient")):
                sanitized[key] = mask_value(item)
            else:
                sanitized[key] = sanitize_for_logs(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_for_logs(item) for item in value]
    return value


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


def first_present(*values):
    for value in values:
        if value not in (None, ""):
            return str(value)
    return ""


MPESA_REFERENCE_KEYS = (
    "mpesa_receipt",
    "mpesa_receipt_number",
    "mpesa_confirmation_code",
    "receipt_number",
    "trans_id",
    "transaction_receipt",
)

ECONFIRM_REFERENCE_KEYS = (
    "release_confirmation_code",
    "buyer_confirmation_code",
    "confirmation_code",
)


def normalize_confirmation_code(value):
    if value in (None, ""):
        return ""
    return str(value).strip().upper()


def first_payload_value_raw(payload, keys):
    if not isinstance(payload, dict):
        return ""

    containers = [payload]
    data = payload.get("data")
    if isinstance(data, dict):
        containers.append(data)
    payment = payload.get("payment")
    if isinstance(payment, dict):
        containers.append(payment)
    elif isinstance(data, dict) and isinstance(data.get("payment"), dict):
        containers.append(data["payment"])

    for container in containers:
        for key in keys:
            value = container.get(key)
            if value not in (None, ""):
                return str(value).strip()

    for container in containers:
        for value in container.values():
            if isinstance(value, dict):
                nested = first_payload_value_raw(value, keys)
                if nested:
                    return nested
    return ""


def extract_payment_references(payload):
    if not isinstance(payload, dict):
        return {"mpesa_receipt": "", "econfirm_code": ""}

    mpesa_receipt = normalize_confirmation_code(
        first_payload_value_raw(payload, MPESA_REFERENCE_KEYS)
    )
    econfirm_code = normalize_confirmation_code(
        first_payload_value_raw(payload, ECONFIRM_REFERENCE_KEYS)
    )
    if mpesa_receipt and econfirm_code == mpesa_receipt:
        econfirm_code = ""
    return {
        "mpesa_receipt": mpesa_receipt,
        "econfirm_code": econfirm_code,
    }


def resolve_release_confirmation_codes(transaction, override=None, external_payload=None):
    codes = []
    normalized_override = normalize_confirmation_code(override)
    if normalized_override:
        codes.append(normalized_override)

    payload = external_payload
    if payload is None and transaction.econfirm_transaction_id:
        payload = EconfirmClient().check_transaction_status(transaction.econfirm_transaction_id)

    if payload:
        references = extract_payment_references(payload)
        for value in (references["mpesa_receipt"], references["econfirm_code"]):
            if value and value not in codes:
                codes.append(value)

    for stored in (
        transaction.mpesa_receipt_number,
        transaction.econfirm_confirmation_code,
    ):
        normalized = normalize_confirmation_code(stored)
        if normalized and normalized not in codes:
            codes.append(normalized)
    return codes


def persist_payment_references(transaction, payload):
    references = extract_payment_references(payload)
    update_fields = []
    if references["mpesa_receipt"] and references["mpesa_receipt"] != transaction.mpesa_receipt_number:
        transaction.mpesa_receipt_number = references["mpesa_receipt"]
        update_fields.append("mpesa_receipt_number")
    if references["econfirm_code"] and references["econfirm_code"] != transaction.econfirm_confirmation_code:
        transaction.econfirm_confirmation_code = references["econfirm_code"]
        update_fields.append("econfirm_confirmation_code")
    if update_fields:
        transaction.payment_provider = "ECONFIRM"
        update_fields.extend(["payment_provider", "updated_at"])
        transaction.save(update_fields=update_fields)
    return references


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

        validate_kenyan_mobile(transaction.client.phone_number, "Your profile")
        seller_phone = validate_kenyan_mobile(transaction.tasker.phone_number, "The accepted tasker profile")

        # eConfirm v1 creates a principal escrow amount. TaskiT tracks the
        # platform fee post-paid, so the client funds only the agreed task amount.
        # Keep this payload aligned with eConfirm's escrow transaction schema;
        # payer phone belongs to the follow-up STK push call.
        payload = {
            "buyer_email": transaction.client.email,
            "seller_email": transaction.tasker.email,
            "receiver_phone": seller_phone,
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

        transaction_id = first_present(data.get("id"), data.get("transaction_id"))
        checkout_request_id = first_present(
            data.get("checkout_request_id"),
            data.get("checkout_id"),
            data.get("transaction_id"),
            transaction_id,
        )

        transaction.econfirm_transaction_id = transaction_id
        transaction.econfirm_checkout_request_id = checkout_request_id
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
        response = self._post("/payments/stk-push", payload, "Failed to initiate eConfirm STK push")
        data = response.get("data", response)
        checkout_request_id = first_present(
            data.get("checkout_request_id"),
            data.get("checkout_id"),
            data.get("transaction_id"),
            data.get("id"),
        )
        if checkout_request_id and checkout_request_id != transaction.econfirm_checkout_request_id:
            transaction.econfirm_checkout_request_id = checkout_request_id
            transaction.save(update_fields=["econfirm_checkout_request_id", "updated_at"])
        return response

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
            payload = response.json()
            if isinstance(payload, dict) and payload.get("success") is False:
                logger.warning(
                    "eConfirm status check rejected for %s: %s",
                    econfirm_transaction_id,
                    sanitize_for_logs(payload),
                )
                return None
            return payload
        except requests.RequestException:
            logger.exception("eConfirm status check failed")
            return None

    def release_funds(self, transaction, confirmation_code=None, external_payload=None):
        if self.mock:
            logger.info("MOCK: eConfirm release skipped for transaction %s", transaction.id)
            return {"status": "released"}

        notes = (
            "Client confirmed completion in TaskiT. "
            "eConfirm releases to the seller configured on the escrow transaction."
        )
        codes = resolve_release_confirmation_codes(
            transaction,
            override=confirmation_code,
            external_payload=external_payload,
        )
        if not codes:
            raise ValidationError(
                "confirmation_code is required for eConfirm release. "
                "Use the M-Pesa receipt from the STK payment SMS or the code shown in eConfirm."
            )

        last_error = None
        for code in codes:
            payload_variants = [
                {"confirmation_code": code, "notes": notes},
                {"mpesa_confirmation_code": code, "notes": notes},
                {
                    "confirmation_code": code,
                    "mpesa_confirmation_code": code,
                    "notes": notes,
                },
            ]
            for payload in payload_variants:
                try:
                    return self._post(
                        f"/transactions/{transaction.econfirm_transaction_id}/release",
                        payload,
                        "Failed to release eConfirm funds",
                    )
                except ValidationError as exc:
                    message = str(exc).lower()
                    if "invalid confirmation" in message or "confirmation code" in message:
                        last_error = exc
                        continue
                    raise

        if last_error is not None:
            raise last_error
        raise ValidationError("Failed to release eConfirm funds.")

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
            logger.warning("eConfirm request %s payload=%s", path, sanitize_for_logs(payload))
            response = requests.post(
                f"{self.base_url}{path}",
                json=payload,
                headers=self._headers(),
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            logger.warning("eConfirm response %s data=%s", path, sanitize_for_logs(data))
            if data.get("success") is False:
                message = data.get("message") or data.get("error") or "Request was rejected by eConfirm"
                errors = data.get("errors")
                if errors:
                    message = f"{message}: {errors}"
                raise ValidationError(f"{error_message}: {message}")
            return data
        except requests.RequestException as exc:
            response = getattr(exc, "response", None)
            details = self._response_error_details(response)
            logger.exception(
                "eConfirm API error on %s details=%s payload=%s",
                path,
                details,
                sanitize_for_logs(payload),
            )
            raise ValidationError(f"{error_message}: {exc}{details}") from exc

    def _response_error_details(self, response):
        if response is None:
            return ""

        try:
            body = response.json()
        except (ValueError, JSONDecodeError):
            body = response.text[:1000].strip()

        trace_headers = {
            key: value
            for key, value in response.headers.items()
            if key.lower()
            in {
                "x-request-id",
                "x-correlation-id",
                "x-trace-id",
                "cf-ray",
                "date",
                "server",
            }
        }
        details = {
            "status_code": response.status_code,
            "body": sanitize_for_logs(body),
            "headers": sanitize_for_logs(trace_headers),
        }
        return f" - {details}"
