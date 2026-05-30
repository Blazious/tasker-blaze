from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Bid, Task, TaskCategory


class AdminMarketplaceGuardTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        self.client_user = User.objects.create_user(
            email="task.client@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Task Client",
            phone_number="+254700000001",
            is_verified=True,
        )
        self.tasker = User.objects.create_user(
            email="tasker.guard@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Tasker Guard",
            phone_number="+254700000002",
            is_verified=True,
            is_tasker_active=True,
        )
        self.category = TaskCategory.objects.get(slug="laundry")
        self.task = Task.objects.create(
            client=self.client_user,
            title="Guarded task",
            description="Marketplace task",
            category=self.category,
            budget_min=Decimal("100.00"),
            budget_max=Decimal("150.00"),
            location_landmark="Library",
        )
        self.api_client = APIClient()

    def test_admin_cannot_post_marketplace_task(self):
        self.api_client.force_authenticate(self.admin)

        response = self.api_client.post(
            "/api/v1/tasks/",
            {
                "title": "Admin task",
                "description": "Admin should not post this.",
                "category": self.category.id,
                "budget_min": "100.00",
                "budget_max": "150.00",
                "location_landmark": "Library",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_cannot_bid_on_marketplace_task(self):
        self.admin.is_tasker_active = True
        self.admin.save(update_fields=["is_tasker_active"])
        self.api_client.force_authenticate(self.admin)

        response = self.api_client.post(
            f"/api/v1/tasks/{self.task.id}/bids/",
            {"amount": "120.00", "message": "Admin bid"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_cannot_accept_marketplace_bid(self):
        self.task.client = self.admin
        self.task.save(update_fields=["client", "updated_at"])
        bid = Bid.objects.create(
            task=self.task,
            tasker=self.tasker,
            amount=Decimal("120.00"),
            message="Normal bid",
        )
        self.api_client.force_authenticate(self.admin)

        response = self.api_client.post(
            f"/api/v1/tasks/{self.task.id}/bids/{bid.id}/accept/",
            format="json",
        )

        self.assertEqual(response.status_code, 403)
