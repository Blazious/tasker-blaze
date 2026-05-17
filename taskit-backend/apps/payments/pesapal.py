import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

TOKEN_CACHE = {
    "token": "",
    "expires_at": None,
}

SANDBOX_BASE_URL = "https://cybqa.pesapal.com/pesapalv3"
PRODUCTION_BASE_URL = "https://pay.pesapal.com/v3"


class PesapalClient:
    def __init__(self):
        self.base_url = (
            PRODUCTION_BASE_URL
            if settings.PESAPAL_ENV == "production"
            else SANDBOX_BASE_URL
        )
        self.consumer_key = settings.PESAPAL_CONSUMER_KEY
        self.consumer_secret = settings.PESAPAL_CONSUMER_SECRET

    def get_access_token(self):
        expires_at = TOKEN_CACHE.get("expires_at")
        if TOKEN_CACHE.get("token") and expires_at and expires_at > timezone.now():
            return TOKEN_CACHE["token"]

        response = requests.post(
            f"{self.base_url}/api/Auth/RequestToken",
            json={
                "consumer_key": self.consumer_key,
                "consumer_secret": self.consumer_secret,
            },
            timeout=20,
        )
        response.raise_for_status()
        token = response.json()["token"]

        TOKEN_CACHE["token"] = token
        TOKEN_CACHE["expires_at"] = timezone.now() + timedelta(minutes=4)
        return token

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def register_ipn(self, ipn_url):
        response = requests.post(
            f"{self.base_url}/api/URLSetup/RegisterIPN",
            json={
                "url": ipn_url,
                "ipn_notification_type": "POST",
            },
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json().get("ipn_id")

    def submit_order(self, transaction, phone_number, description):
        if settings.PESAPAL_MOCK:
            logger.info(
                "MOCK: Pesapal payment skipped for transaction %s",
                transaction.id,
            )
            transaction.pesapal_order_id = f"mock-{transaction.id}"
            transaction.save(update_fields=["pesapal_order_id", "updated_at"])
            return f"/mock-payment?transaction_id={transaction.id}"

        full_name_parts = transaction.client.full_name.split()
        first_name = full_name_parts[0] if full_name_parts else ""
        last_name = full_name_parts[-1] if len(full_name_parts) > 1 else first_name

        response = requests.post(
            f"{self.base_url}/api/Transactions/SubmitOrderRequest",
            json={
                "id": str(transaction.id),
                "currency": "KES",
                "amount": float(transaction.total_charged),
                "description": description,
                "callback_url": settings.PESAPAL_CALLBACK_URL,
                "notification_id": settings.PESAPAL_IPN_ID,
                "billing_address": {
                    "phone_number": phone_number,
                    "email_address": transaction.client.email,
                    "first_name": first_name,
                    "last_name": last_name,
                },
            },
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()

        transaction.pesapal_order_id = data.get("order_tracking_id", "")
        transaction.save(update_fields=["pesapal_order_id", "updated_at"])
        return data["redirect_url"]

    def get_transaction_status(self, order_tracking_id):
        response = requests.get(
            f"{self.base_url}/api/Transactions/GetTransactionStatus",
            params={"orderTrackingId": order_tracking_id},
            headers=self._headers(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()
