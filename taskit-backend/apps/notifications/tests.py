from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.payments.models import Transaction
from apps.reviews.models import Review
from apps.tasks.models import Bid, Task, TaskCategory

from .models import Notification
from .utils import send_notification


class NotificationTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client_user = User.objects.create_user(
            email="notify.client@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Notify Client",
            phone_number="+254700000001",
            is_verified=True,
        )
        self.tasker = User.objects.create_user(
            email="notify.tasker@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Notify Tasker",
            phone_number="+254700000002",
            is_verified=True,
            is_tasker_active=True,
        )
        self.category = TaskCategory.objects.get(slug="laundry")
        self.task = Task.objects.create(
            client=self.client_user,
            title="Notification task",
            description="Task for notifications",
            category=self.category,
            budget_min=Decimal("100.00"),
            budget_max=Decimal("200.00"),
            location_landmark="Library",
        )

    def test_send_notification_creates_record(self):
        notification = send_notification(
            recipient=self.client_user,
            notification_type=Notification.Type.NEW_BID,
            title="Hello",
            body="A notification body",
            related_task=self.task,
        )

        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(notification.recipient, self.client_user)
        self.assertFalse(notification.is_read)

    def test_bid_signals_create_new_bid_and_accepted_notifications(self):
        bid = Bid.objects.create(
            task=self.task,
            tasker=self.tasker,
            amount=Decimal("150.00"),
            message="Ready",
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.client_user,
                notification_type=Notification.Type.NEW_BID,
            ).exists()
        )

        bid.status = Bid.Status.ACCEPTED
        bid.save(update_fields=["status"])

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.tasker,
                notification_type=Notification.Type.BID_ACCEPTED,
            ).exists()
        )

    def test_transaction_status_signal_creates_payment_notification(self):
        transaction = Transaction.objects.create(
            task=self.task,
            client=self.client_user,
            tasker=self.tasker,
            agreed_amount=Decimal("150.00"),
        )
        transaction.status = Transaction.Status.ESCROWED
        transaction.save(update_fields=["status"])

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.tasker,
                notification_type=Notification.Type.PAYMENT_RECEIVED,
                title="Payment secured",
            ).exists()
        )

    def test_review_visibility_signal_creates_review_notification(self):
        self.task.status = Task.Status.COMPLETED
        self.task.assigned_tasker = self.tasker
        self.task.save(update_fields=["status", "assigned_tasker", "updated_at"])
        review = Review.objects.create(
            task=self.task,
            reviewer=self.client_user,
            reviewee=self.tasker,
            rating=5,
            comment="Great work",
            review_type=Review.ReviewType.CLIENT_TO_TASKER,
        )

        review.is_visible = True
        review.save(update_fields=["is_visible"])

        self.assertTrue(
            Notification.objects.filter(
                recipient=self.tasker,
                notification_type=Notification.Type.REVIEW_RECEIVED,
            ).exists()
        )

    def test_unread_count_and_read_endpoints(self):
        first = send_notification(
            self.client_user,
            Notification.Type.NEW_BID,
            "One",
            "Body",
            self.task,
        )
        send_notification(
            self.client_user,
            Notification.Type.NEW_BID,
            "Two",
            "Body",
            self.task,
        )
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        count_response = api_client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(count_response.status_code, 200)
        self.assertEqual(count_response.data["count"], 2)

        read_response = api_client.post(f"/api/v1/notifications/{first.id}/read/")
        self.assertEqual(read_response.status_code, 200)

        count_response = api_client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(count_response.data["count"], 1)

        read_all_response = api_client.post("/api/v1/notifications/read-all/")
        self.assertEqual(read_all_response.status_code, 200)

        count_response = api_client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(count_response.data["count"], 0)
