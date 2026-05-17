from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.tasks.models import Bid, Task, TaskCategory

from .models import ChatThread, Message


class ChatTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.client_user = User.objects.create_user(
            email="chat.client@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Chat Client",
            phone_number="+254700000001",
            is_verified=True,
        )
        self.tasker = User.objects.create_user(
            email="chat.tasker@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Chat Tasker",
            phone_number="+254700000002",
            is_verified=True,
            is_tasker_active=True,
        )
        self.outsider = User.objects.create_user(
            email="chat.outsider@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="Chat Outsider",
            phone_number="+254700000003",
            is_verified=True,
        )
        self.category = TaskCategory.objects.get(slug="laundry")
        self.task = Task.objects.create(
            client=self.client_user,
            title="Chat task",
            description="A task with chat",
            category=self.category,
            budget_min=Decimal("100.00"),
            budget_max=Decimal("200.00"),
            location_landmark="Library",
        )
        self.bid = Bid.objects.create(
            task=self.task,
            tasker=self.tasker,
            amount=Decimal("150.00"),
            message="Ready to help",
        )

    def test_chat_thread_is_created_when_bid_is_accepted(self):
        self.bid.status = Bid.Status.ACCEPTED
        self.bid.save(update_fields=["status"])

        thread = ChatThread.objects.get(task=self.task)
        self.assertTrue(thread.participants.filter(id=self.client_user.id).exists())
        self.assertTrue(thread.participants.filter(id=self.tasker.id).exists())

    def test_rest_message_endpoint_allows_participants(self):
        self.bid.status = Bid.Status.ACCEPTED
        self.bid.save(update_fields=["status"])
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.post(
            f"/api/v1/chat/{self.task.id}/messages/",
            {"content": "Hello there"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.count(), 1)

    def test_rest_message_endpoint_blocks_non_participants(self):
        self.bid.status = Bid.Status.ACCEPTED
        self.bid.save(update_fields=["status"])
        api_client = APIClient()
        api_client.force_authenticate(self.outsider)

        response = api_client.get(f"/api/v1/chat/{self.task.id}/messages/")

        self.assertEqual(response.status_code, 403)

    def test_my_threads_lists_user_threads_with_preview(self):
        self.bid.status = Bid.Status.ACCEPTED
        self.bid.save(update_fields=["status"])
        thread = ChatThread.objects.get(task=self.task)
        Message.objects.create(
            thread=thread,
            sender=self.tasker,
            content="Last message",
        )
        api_client = APIClient()
        api_client.force_authenticate(self.client_user)

        response = api_client.get("/api/v1/chat/my-threads/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["task_id"], self.task.id)
        self.assertEqual(response.data[0]["last_message"]["content"], "Last message")
