from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.db import transaction
from django.test import TestCase
from rest_framework.test import APIClient

from apps.tasks.models import Task, TaskCategory

from .badges import get_badges
from .models import Review


class ReviewTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client_user = User.objects.create_user(
            email="review.client@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Review Client",
            phone_number="+254700000001",
            is_verified=True,
        )
        self.tasker = User.objects.create_user(
            email="review.tasker@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Review Tasker",
            phone_number="+254700000002",
            is_verified=True,
            is_tasker_active=True,
            department="Computer Science",
            year_of_study=3,
            bio="Reliable campus helper.",
        )
        self.category = TaskCategory.objects.get(slug="laundry")
        self.task = self.create_completed_task("Review task")

    def create_completed_task(self, title):
        return Task.objects.create(
            client=self.client_user,
            title=title,
            description="Completed task",
            category=self.category,
            budget_min=Decimal("100.00"),
            budget_max=Decimal("200.00"),
            location_landmark="Library",
            status=Task.Status.COMPLETED,
            assigned_tasker=self.tasker,
        )

    def test_review_unique_together_constraint(self):
        Review.objects.create(
            task=self.task,
            reviewer=self.client_user,
            reviewee=self.tasker,
            rating=5,
            comment="Great work",
            review_type=Review.ReviewType.CLIENT_TO_TASKER,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    task=self.task,
                    reviewer=self.client_user,
                    reviewee=self.tasker,
                    rating=4,
                    comment="Trying again",
                    review_type=Review.ReviewType.CLIENT_TO_TASKER,
                )

    def test_reviews_become_visible_only_after_both_parties_review(self):
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        first_response = api_client.post(
            f"/api/v1/reviews/submit/{self.task.id}/",
            {"rating": 5, "comment": "Excellent work"},
            format="json",
        )
        self.assertEqual(first_response.status_code, 201)
        self.assertFalse(Review.objects.get(id=first_response.data["id"]).is_visible)

        api_client.force_authenticate(self.tasker)
        second_response = api_client.post(
            f"/api/v1/reviews/submit/{self.task.id}/",
            {"rating": 5, "comment": "Clear instructions"},
            format="json",
        )
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(Review.objects.filter(task=self.task, is_visible=True).count(), 2)

    def test_get_badges_returns_expected_badges(self):
        for index in range(20):
            task = self.create_completed_task(f"Badge task {index}")
            Review.objects.create(
                task=task,
                reviewer=self.client_user,
                reviewee=self.tasker,
                rating=5,
                comment="Excellent",
                review_type=Review.ReviewType.CLIENT_TO_TASKER,
                is_visible=True,
            )

        self.assertEqual(
            get_badges(self.tasker),
            ["First Task", "Rising Star", "Top Rated", "Trusted Tasker"],
        )

    def test_public_profile_returns_reputation_data(self):
        Review.objects.create(
            task=self.task,
            reviewer=self.client_user,
            reviewee=self.tasker,
            rating=5,
            comment="Excellent work",
            review_type=Review.ReviewType.CLIENT_TO_TASKER,
            is_visible=True,
        )
        api_client = APIClient()

        response = api_client.get(f"/api/v1/profiles/{self.tasker.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["full_name"], self.tasker.full_name)
        self.assertEqual(response.data["average_rating"], 5.0)
        self.assertEqual(response.data["rating_breakdown"]["communication"], 5.0)
        self.assertEqual(response.data["rating_breakdown"]["punctuality"], 5.0)
        self.assertEqual(response.data["rating_breakdown"]["quality"], 5.0)
        self.assertEqual(response.data["total_reviews"], 1)
        self.assertEqual(response.data["completed_tasks_count"], 1)
        self.assertEqual(response.data["badges"], ["First Task"])
        self.assertEqual(response.data["recent_reviews"][0]["comment"], "Excellent work")
        self.assertEqual(response.data["completed_task_history"][0]["title"], self.task.title)

    def test_submit_review_accepts_category_ratings(self):
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.post(
            f"/api/v1/reviews/submit/{self.task.id}/",
            {
                "rating": 4,
                "communication_rating": 5,
                "punctuality_rating": 4,
                "quality_rating": 3,
                "comment": "Good communication and decent work",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["communication_rating"], 5)
        self.assertEqual(response.data["punctuality_rating"], 4)
        self.assertEqual(response.data["quality_rating"], 3)
        self.assertEqual(response.data["rating"], 4)
