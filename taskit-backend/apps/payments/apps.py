from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"

    def ready(self):
        from django.conf import settings

        from . import signals  # noqa: F401

        if not getattr(settings, "PESAPAL_REGISTER_IPN_ON_STARTUP", False):
            return

        try:
            from .pesapal import PesapalClient

            ipn_url = getattr(settings, "PESAPAL_IPN_URL", "")
            if ipn_url:
                PesapalClient().register_ipn(ipn_url)
        except Exception:
            pass
