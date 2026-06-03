from decimal import Decimal
from datetime import timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.tasks.models import Bid, Task, TaskCategory

from .billing import generate_invoice_for_month, overdue_balance
from .escrow import hold_funds, release_funds
from .econfirm import normalize_kenyan_phone, validate_kenyan_mobile
from .models import EscrowLedger, PlatformFeeUsage, PlatformInvoice, Transaction


class PaymentTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client_user = User.objects.create_user(
            email="client@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Client User",
            phone_number="+254700000001",
            is_verified=True,
        )
        self.tasker = User.objects.create_user(
            email="tasker@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Tasker User",
            phone_number="+254700000002",
            is_verified=True,
            is_tasker_active=True,
        )
        self.category = TaskCategory.objects.get(slug="laundry")
        self.task = Task.objects.create(
            client=self.client_user,
            title="Wash clothes",
            description="Wash and fold",
            category=self.category,
            budget_min=Decimal("180.00"),
            budget_max=Decimal("220.00"),
            location_landmark="Hostels Block A",
            status=Task.Status.ASSIGNED,
            assigned_tasker=self.tasker,
        )
        self.bid = Bid.objects.create(
            task=self.task,
            tasker=self.tasker,
            amount=Decimal("200.00"),
            message="I can do it.",
            status=Bid.Status.PENDING,
        )

    def create_transaction(self, status=Transaction.Status.PENDING_PAYMENT):
        return Transaction.objects.create(
            task=self.task,
            client=self.client_user,
            tasker=self.tasker,
            agreed_amount=Decimal("200.00"),
            status=status,
        )

    def test_transaction_auto_calculates_amounts_on_save(self):
        transaction = self.create_transaction()

        self.assertEqual(transaction.platform_fee, Decimal("20.00"))
        self.assertEqual(transaction.tasker_payout, Decimal("200.00"))
        self.assertEqual(transaction.total_charged, Decimal("200.00"))

    def test_phone_normalization_accepts_common_kenyan_mobile_formats(self):
        self.assertEqual(normalize_kenyan_phone("0712472743"), "254712472743")
        self.assertEqual(normalize_kenyan_phone("+254712472743"), "254712472743")
        self.assertEqual(normalize_kenyan_phone("0112472743"), "254112472743")

    def test_phone_validation_rejects_bad_receiver_phone(self):
        with self.assertRaises(Exception):
            validate_kenyan_mobile("2541124727432", "Tasker")

    @patch("apps.payments.escrow.send_notification")
    def test_hold_funds_sets_transaction_and_task_statuses(self, _mock_notify):
        transaction = self.create_transaction()

        hold_funds(transaction)
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(transaction.status, Transaction.Status.ESCROWED)
        self.assertIsNotNone(transaction.paid_at)
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)
        self.assertEqual(transaction.ledger_entries.count(), 1)

    @patch("apps.payments.escrow.send_notification")
    def test_release_funds_writes_fee_and_payout_entries(self, _mock_notify):
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)

        release_funds(transaction)
        transaction.refresh_from_db()

        self.assertEqual(transaction.status, Transaction.Status.RELEASED)
        self.assertEqual(transaction.ledger_entries.count(), 1)
        self.assertTrue(
            transaction.ledger_entries.filter(
                action=EscrowLedger.Action.RELEASE,
                amount=Decimal("200.00"),
            ).exists()
        )

    @patch("apps.payments.escrow.send_notification")
    def test_release_funds_tracks_billable_platform_fee_after_trial(self, _mock_notify):
        self.tasker.date_joined = timezone.now() - timedelta(days=20)
        self.tasker.save(update_fields=["date_joined"])
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)

        release_funds(transaction)

        usage = PlatformFeeUsage.objects.get(transaction=transaction)
        self.assertFalse(usage.is_trial_usage)
        self.assertEqual(usage.status, PlatformFeeUsage.Status.TRACKED)
        self.assertEqual(usage.fee_amount, Decimal("20.00"))

    @patch("apps.payments.escrow.send_notification")
    def test_release_funds_waives_platform_fee_during_trial(self, _mock_notify):
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)

        release_funds(transaction)

        usage = PlatformFeeUsage.objects.get(transaction=transaction)
        self.assertTrue(usage.is_trial_usage)
        self.assertEqual(usage.status, PlatformFeeUsage.Status.WAIVED)
        self.assertEqual(usage.fee_amount, Decimal("0.00"))

    @patch("apps.payments.escrow.send_notification")
    def test_generate_invoice_uses_three_day_grace_period(self, _mock_notify):
        self.tasker.date_joined = timezone.now() - timedelta(days=20)
        self.tasker.save(update_fields=["date_joined"])
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)
        release_funds(transaction)

        invoice = generate_invoice_for_month(self.tasker)

        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.amount, Decimal("20.00"))
        self.assertGreater(invoice.due_date, timezone.now() + timedelta(days=2))
        self.assertLess(invoice.due_date, timezone.now() + timedelta(days=4))
        self.assertEqual(
            PlatformFeeUsage.objects.get(transaction=transaction).status,
            PlatformFeeUsage.Status.INVOICED,
        )

    def test_overdue_balance_counts_pending_invoices_after_grace_period(self):
        PlatformInvoice.objects.create(
            tasker=self.tasker,
            billing_month=timezone.now().date().replace(day=1),
            amount=Decimal("45.00"),
            due_date=timezone.now() - timedelta(days=1),
        )

        self.assertEqual(overdue_balance(self.tasker), Decimal("45.00"))

    def test_release_funds_raises_if_transaction_is_not_escrowed(self):
        transaction = self.create_transaction()

        with self.assertRaises(ValueError):
            release_funds(transaction)

    @patch("apps.payments.econfirm.EconfirmClient.check_transaction_status")
    @patch("apps.payments.escrow.send_notification")
    def test_payment_status_reconciles_wrapped_econfirm_payload(self, _mock_notify, mock_status):
        mock_status.return_value = {
            "success": True,
            "data": {"status": "funds_held", "id": "txn_wrapped"},
        }
        transaction = self.create_transaction()
        transaction.econfirm_transaction_id = "txn_wrapped"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.get(f"/api/v1/payments/status/{self.task.id}/")
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["synced"])
        self.assertEqual(transaction.status, Transaction.Status.ESCROWED)
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    @override_settings(ECONFIRM_MOCK=True)
    @patch("apps.payments.escrow.send_notification")
    def test_payment_status_reconciles_funded_econfirm_into_local_db(self, _mock_notify):
        transaction = self.create_transaction()
        transaction.econfirm_transaction_id = "txn_status_sync"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.get(f"/api/v1/payments/status/{self.task.id}/")
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["synced"])
        self.assertEqual(response.data["status"], Transaction.Status.ESCROWED)
        self.assertEqual(response.data["task_status"], Task.Status.IN_PROGRESS)
        self.assertEqual(transaction.status, Transaction.Status.ESCROWED)
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    @override_settings(ECONFIRM_MOCK=True)
    @patch("apps.payments.escrow.send_notification")
    def test_mark_task_complete_sets_tasker_completed_at(self, _mock_notify):
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)
        transaction.econfirm_transaction_id = "txn_mark_complete"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        self.task.status = Task.Status.IN_PROGRESS
        self.task.save(update_fields=["status", "updated_at"])
        api_client = APIClient()
        api_client.force_authenticate(self.tasker)

        response = api_client.post(f"/api/v1/tasks/{self.task.id}/mark-complete/")
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.task.tasker_completed_at)
        self.assertIsNotNone(response.data["tasker_completed_at"])

    @override_settings(ECONFIRM_MOCK=True)
    @patch("apps.payments.escrow.send_notification")
    def test_client_release_endpoint_completes_task(self, _mock_notify):
        self.task.status = Task.Status.IN_PROGRESS
        self.task.tasker_completed_at = timezone.now()
        self.task.save(update_fields=["status", "tasker_completed_at", "updated_at"])
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)
        transaction.econfirm_transaction_id = "txn_client_release"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.post(f"/api/v1/payments/release/{self.task.id}/")
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transaction.status, Transaction.Status.RELEASED)
        self.assertEqual(self.task.status, Task.Status.COMPLETED)

    @patch("apps.payments.econfirm.EconfirmClient.check_transaction_status")
    @patch("apps.payments.escrow.send_notification")
    def test_payment_status_reconciles_manual_dashboard_release(self, _mock_notify, mock_status):
        self.tasker.date_joined = timezone.now() - timedelta(days=20)
        self.tasker.save(update_fields=["date_joined"])
        self.task.status = Task.Status.IN_PROGRESS
        self.task.tasker_completed_at = timezone.now()
        self.task.save(update_fields=["status", "tasker_completed_at", "updated_at"])
        mock_status.return_value = {"success": True, "data": {"status": "released"}}
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)
        transaction.econfirm_transaction_id = "txn_manual_release"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.get(f"/api/v1/payments/status/{self.task.id}/")
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["synced"])
        self.assertEqual(transaction.status, Transaction.Status.RELEASED)
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertTrue(PlatformFeeUsage.objects.filter(transaction=transaction).exists())

    @override_settings(ECONFIRM_MOCK=True)
    @patch("apps.payments.escrow.send_notification")
    def test_review_after_completion_appears_on_tasker_profile(self, _mock_notify):
        from apps.reviews.models import Review

        self.task.status = Task.Status.IN_PROGRESS
        self.task.tasker_completed_at = timezone.now()
        self.task.save(update_fields=["status", "tasker_completed_at", "updated_at"])
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)
        transaction.econfirm_transaction_id = "txn_review_flow"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)
        api_client.post(f"/api/v1/payments/release/{self.task.id}/")
        self.task.refresh_from_db()

        api_client.force_authenticate(self.client_user)
        review_response = api_client.post(
            f"/api/v1/reviews/submit/{self.task.id}/",
            {
                "rating": 5,
                "communication_rating": 5,
                "punctuality_rating": 5,
                "quality_rating": 5,
                "comment": "Great laundry service",
            },
            format="json",
        )
        self.assertEqual(review_response.status_code, 201)

        profile_response = api_client.get(f"/api/v1/profiles/{self.tasker.id}/")
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.data["completed_tasks_count"], 1)
        self.assertEqual(len(profile_response.data["recent_reviews"]), 0)
        Review.objects.filter(task=self.task).update(is_visible=True)
        profile_response = api_client.get(f"/api/v1/profiles/{self.tasker.id}/")
        self.assertEqual(profile_response.data["recent_reviews"][0]["comment"], "Great laundry service")

    @override_settings(ECONFIRM_MOCK=True)
    @patch("apps.payments.escrow.send_notification")
    def test_release_endpoint_syncs_funded_econfirm_before_release(self, _mock_notify):
        self.task.tasker_completed_at = timezone.now()
        self.task.save(update_fields=["tasker_completed_at", "updated_at"])
        transaction = self.create_transaction()
        transaction.econfirm_transaction_id = "mock-econfirm-release"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.post(f"/api/v1/payments/release/{self.task.id}/")
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transaction.status, Transaction.Status.RELEASED)
        self.assertEqual(self.task.status, Task.Status.COMPLETED)

    def test_ipn_callback_returns_200_for_bad_payload(self):
        api_client = APIClient()

        response = api_client.post("/api/v1/payments/ipn-callback/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["orderNotificationType"], "IPNCHANGE")

    @override_settings(ECONFIRM_MOCK=True)
    @patch("apps.payments.escrow.send_notification")
    def test_econfirm_callback_holds_funds_on_funded_status(self, _mock_notify):
        transaction = self.create_transaction()
        transaction.econfirm_transaction_id = "txn_test_123"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()

        response = api_client.post(
            "/api/v1/payments/econfirm-callback/",
            {
                "id": "txn_test_123",
                "status": "funded",
                "mpesa_receipt": "RCP123",
                "payment_method": "Mpesa",
            },
            format="json",
        )
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transaction.status, Transaction.Status.ESCROWED)
        self.assertEqual(transaction.mpesa_receipt_number, "RCP123")
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    @patch("apps.payments.escrow.send_notification")
    def test_econfirm_callback_reconciles_manual_release_and_tracks_billing(self, _mock_notify):
        self.tasker.date_joined = timezone.now() - timedelta(days=20)
        self.tasker.save(update_fields=["date_joined"])
        transaction = self.create_transaction(status=Transaction.Status.ESCROWED)
        transaction.econfirm_transaction_id = "txn_released_123"
        transaction.save(update_fields=["econfirm_transaction_id", "updated_at"])
        api_client = APIClient()

        response = api_client.post(
            "/api/v1/payments/econfirm-callback/",
            {
                "id": "txn_released_123",
                "event": "funds.released",
                "status": "released",
            },
            format="json",
        )
        transaction.refresh_from_db()
        self.task.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transaction.status, Transaction.Status.RELEASED)
        self.assertIsNotNone(transaction.released_at)
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertTrue(PlatformFeeUsage.objects.filter(transaction=transaction).exists())

    @override_settings(ECONFIRM_MOCK=True)
    @patch("apps.payments.econfirm.EconfirmClient.create_escrow")
    @patch("apps.payments.econfirm.EconfirmClient.initiate_stk_push")
    def test_initiate_payment_uses_econfirm(self, mock_stk, mock_escrow):
        self.bid.status = Bid.Status.ACCEPTED
        self.bid.save(update_fields=["status"])
        mock_escrow.return_value = {
            "success": True,
            "data": {
                "id": "txn_test_123",
                "status": "pending",
                "checkout_url": "/mock-payment?transaction_id=1",
            },
        }
        mock_stk.return_value = {"checkout_url": "/mock-payment?transaction_id=1"}
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.post(f"/api/v1/payments/initiate/{self.task.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "ECONFIRM")
        mock_escrow.assert_called_once()
        mock_stk.assert_called_once()

    @override_settings(PESAPAL_MOCK=True, DEBUG=True)
    @patch("apps.payments.escrow.send_notification")
    def test_mock_confirm_endpoint_escrows_funds(self, _mock_notify):
        transaction = self.create_transaction()
        api_client = APIClient()

        response = api_client.get(f"/api/v1/payments/mock-confirm/{transaction.id}/")
        transaction.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(transaction.status, Transaction.Status.ESCROWED)

    def test_admin_can_list_platform_invoices(self):
        admin = get_user_model().objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        PlatformInvoice.objects.create(
            tasker=self.tasker,
            billing_month=timezone.now().date().replace(day=1),
            amount=Decimal("20.00"),
            due_date=timezone.now() + timedelta(days=3),
        )
        api_client = APIClient()
        api_client.force_authenticate(admin)

        response = api_client.get("/api/v1/payments/admin/platform-invoices/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["tasker"]["email"], self.tasker.email)
        self.assertEqual(response.data[0]["amount"], "20.00")

    def test_admin_can_waive_platform_invoice_and_usage(self):
        admin = get_user_model().objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        transaction = self.create_transaction(status=Transaction.Status.RELEASED)
        invoice = PlatformInvoice.objects.create(
            tasker=self.tasker,
            billing_month=timezone.now().date().replace(day=1),
            amount=Decimal("20.00"),
            due_date=timezone.now() + timedelta(days=3),
        )
        usage = PlatformFeeUsage.objects.create(
            tasker=self.tasker,
            transaction=transaction,
            task=self.task,
            task_amount=Decimal("200.00"),
            fee_amount=Decimal("20.00"),
            billing_month=invoice.billing_month,
            status=PlatformFeeUsage.Status.INVOICED,
            invoice=invoice,
        )
        api_client = APIClient()
        api_client.force_authenticate(admin)

        response = api_client.patch(
            f"/api/v1/payments/admin/platform-invoices/{invoice.id}/",
            {
                "status": PlatformInvoice.Status.WAIVED,
                "notes": "Waived as launch-period goodwill.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        usage.refresh_from_db()
        self.assertEqual(invoice.status, PlatformInvoice.Status.WAIVED)
        self.assertEqual(invoice.notes, "Waived as launch-period goodwill.")
        self.assertEqual(usage.status, PlatformFeeUsage.Status.WAIVED)

    def test_admin_cannot_manually_mark_platform_invoice_paid(self):
        admin = get_user_model().objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        invoice = PlatformInvoice.objects.create(
            tasker=self.tasker,
            billing_month=timezone.now().date().replace(day=1),
            amount=Decimal("20.00"),
            due_date=timezone.now() + timedelta(days=3),
        )
        api_client = APIClient()
        api_client.force_authenticate(admin)

        response = api_client.patch(
            f"/api/v1/payments/admin/platform-invoices/{invoice.id}/",
            {"status": PlatformInvoice.Status.PAID},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(
        INTASEND_SECRET_KEY="ISSecretKey_test_mock",
        INTASEND_BASE_URL="https://sandbox.intasend.com/api/v1",
    )
    @patch("apps.payments.intasend.requests.post")
    def test_platform_invoice_payment_sends_whole_shilling_amount(self, mock_post):
        invoice = PlatformInvoice.objects.create(
            tasker=self.tasker,
            billing_month=timezone.now().date().replace(day=1),
            amount=Decimal("70.00"),
            due_date=timezone.now() + timedelta(days=3),
        )
        response_mock = Mock()
        response_mock.raise_for_status.return_value = None
        response_mock.json.return_value = {
            "invoice_id": "intasend-invoice-123",
            "checkout_id": "checkout-123",
        }
        mock_post.return_value = response_mock
        api_client = APIClient()
        api_client.force_authenticate(self.tasker)

        response = api_client.post(f"/api/v1/payments/platform-invoices/{invoice.id}/pay/")

        self.assertEqual(response.status_code, 200)
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["amount"], "70")
        self.assertEqual(payload["phone_number"], "254700000002")
        self.assertEqual(payload["email"], self.tasker.email)
        self.assertEqual(payload["currency"], "KES")
        self.assertEqual(payload["narrative"], f"TaskiT platform invoice #{invoice.id}")

    @override_settings(
        INTASEND_SECRET_KEY="ISSecretKey_test_mock",
        INTASEND_BASE_URL="https://sandbox.intasend.com/api/v1",
    )
    @patch("apps.payments.intasend.requests.post")
    def test_platform_invoice_payment_rejects_fractional_mpesa_amount(self, mock_post):
        invoice = PlatformInvoice.objects.create(
            tasker=self.tasker,
            billing_month=timezone.now().date().replace(day=1),
            amount=Decimal("70.50"),
            due_date=timezone.now() + timedelta(days=3),
        )
        api_client = APIClient()
        api_client.force_authenticate(self.tasker)

        response = api_client.post(f"/api/v1/payments/platform-invoices/{invoice.id}/pay/")

        self.assertEqual(response.status_code, 400)
        mock_post.assert_not_called()
