from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient


class AdminOverviewTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.student = User.objects.create_user(
            email="support.user@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Support User",
            phone_number="+254700000020",
            is_verified=True,
        )
        self.admin = User.objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        self.api_client = APIClient()

    def test_admin_overview_requires_staff_user(self):
        self.api_client.force_authenticate(self.student)

        response = self.api_client.get("/api/v1/support/admin/overview/")

        self.assertEqual(response.status_code, 403)

    def test_admin_overview_returns_platform_metrics_for_staff(self):
        self.api_client.force_authenticate(self.admin)

        response = self.api_client.get("/api/v1/support/admin/overview/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("users", response.data)
        self.assertIn("tasks", response.data)
        self.assertIn("ops", response.data)
        self.assertIn("billing", response.data)
