from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.utils import send_notification
from apps.payments.econfirm import EconfirmClient
from apps.payments.escrow import hold_funds
from apps.payments.models import Transaction

from .models import Bid, Task, TaskCategory
from .geo import validate_within_hard_geofence
from .serializers import (
    BidCreateSerializer,
    BidSerializer,
    TaskCategorySerializer,
    TaskSerializer,
)


class TasksHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"app": "tasks", "status": "ok"})


class TaskPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class TaskCategoryListView(generics.ListAPIView):
    serializer_class = TaskCategorySerializer
    authentication_classes = []
    permission_classes = []

    def get_queryset(self):
        return TaskCategory.objects.filter(is_active=True)


class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = TaskPagination

    def get_queryset(self):
        queryset = (
            Task.objects.filter(status=Task.Status.OPEN)
            .select_related("client", "category", "assigned_tasker")
            .prefetch_related("bids__tasker")
        )

        category_slug = self.request.query_params.get("category")
        location_landmark = self.request.query_params.get("location_landmark")
        budget_min = self.request.query_params.get("budget_min")
        budget_max = self.request.query_params.get("budget_max")
        requires_home_visit = self.request.query_params.get("requires_home_visit")
        preferred_tasker_gender = self.request.query_params.get("preferred_tasker_gender")
        schedule_type = self.request.query_params.get("schedule_type")
        ordering = self.request.query_params.get("ordering", "-created_at")

        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if location_landmark:
            queryset = queryset.filter(location_landmark=location_landmark)
        if budget_min:
            queryset = queryset.filter(budget_max__gte=budget_min)
        if budget_max:
            queryset = queryset.filter(budget_min__lte=budget_max)
        if requires_home_visit is not None:
            value = requires_home_visit.lower()
            if value in ("true", "1", "yes"):
                queryset = queryset.filter(requires_home_visit=True)
            elif value in ("false", "0", "no"):
                queryset = queryset.filter(requires_home_visit=False)
        if preferred_tasker_gender in (
            Task.TaskerGenderPreference.ANY,
            Task.TaskerGenderPreference.FEMALE,
            Task.TaskerGenderPreference.MALE,
        ):
            queryset = queryset.filter(preferred_tasker_gender=preferred_tasker_gender)
        if schedule_type in (Task.ScheduleType.ASAP, Task.ScheduleType.SCHEDULED):
            queryset = queryset.filter(schedule_type=schedule_type)

        if ordering in (
            "created_at",
            "-created_at",
            "budget_max",
            "-budget_max",
            "scheduled_for",
            "-scheduled_for",
        ):
            queryset = queryset.order_by(ordering)

        return queryset


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return (
            Task.objects.select_related("client", "category", "assigned_tasker")
            .prefetch_related("bids__tasker")
            .select_related("transaction")
            .all()
        )

    def perform_update(self, serializer):
        if self.request.user.is_staff or self.request.user.is_superuser:
            raise PermissionDenied("Admin accounts cannot manage marketplace tasks.")
        task = self.get_object()
        if task.client_id != self.request.user.id:
            raise PermissionDenied("Only the task client can update this task.")
        if task.status != Task.Status.OPEN:
            raise ValidationError("Only open tasks can be updated.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied("Admin accounts cannot manage marketplace tasks.")
        task = self.get_object()
        if task.client_id != request.user.id:
            raise PermissionDenied("Only the task client can cancel this task.")
        if task.bids.filter(status=Bid.Status.ACCEPTED).exists():
            raise ValidationError("Tasks with accepted bids cannot be cancelled.")

        task.status = Task.Status.CANCELLED
        task.save(update_fields=["status", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyTasksView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskPagination

    def get_queryset(self):
        return (
            Task.objects.filter(client=self.request.user)
            .filter(client_hidden_at__isnull=True)
            .select_related("client", "category", "assigned_tasker")
            .prefetch_related("bids__tasker")
        )


class MyAssignmentsView(generics.ListAPIView):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskPagination

    def get_queryset(self):
        return (
            Task.objects.filter(assigned_tasker=self.request.user)
            .filter(tasker_hidden_at__isnull=True)
            .select_related("client", "category", "assigned_tasker")
            .prefetch_related("bids__tasker")
        )


class MyBidsView(generics.ListAPIView):
    serializer_class = BidSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = TaskPagination

    def get_queryset(self):
        return (
            Bid.objects.filter(tasker=self.request.user)
            .select_related("task", "task__category", "task__client")
            .order_by("-created_at")
        )


class BidListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_task(self):
        return get_object_or_404(Task.objects.select_related("client"), pk=self.kwargs["task_id"])

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BidCreateSerializer
        return BidSerializer

    def get_queryset(self):
        task = self.get_task()
        user = self.request.user
        queryset = Bid.objects.filter(task=task).select_related("tasker", "task")

        if task.client_id == user.id:
            return queryset
        return queryset.filter(tasker=user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["task"] = self.get_task()
        return context


class AcceptBidView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, task_id, bid_id):
        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied("Admin accounts cannot accept marketplace bids.")
        task = get_object_or_404(Task.objects.select_for_update(), pk=task_id)
        if task.client_id != request.user.id:
            raise PermissionDenied("Only the task client can accept bids.")
        if task.status != Task.Status.OPEN:
            raise ValidationError("Only open tasks can have bids accepted.")
        validate_within_hard_geofence(
            request.data.get("actor_latitude"),
            request.data.get("actor_longitude"),
            "current_location",
        )

        bid = get_object_or_404(
            Bid.objects.select_for_update().select_related("tasker"),
            pk=bid_id,
            task=task,
        )

        Bid.objects.filter(task=task).exclude(pk=bid.pk).update(status=Bid.Status.REJECTED)
        bid.status = Bid.Status.ACCEPTED
        bid.save(update_fields=["status"])

        task.status = Task.Status.ASSIGNED
        task.assigned_tasker = bid.tasker
        task.assigned_at = timezone.now()
        task.save(
            update_fields=["status", "assigned_tasker", "assigned_at", "updated_at"]
        )

        return Response(BidSerializer(bid).data)


class RejectBidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id, bid_id):
        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied("Admin accounts cannot reject marketplace bids.")
        task = get_object_or_404(Task, pk=task_id)
        if task.client_id != request.user.id:
            raise PermissionDenied("Only the task client can reject bids.")

        bid = get_object_or_404(Bid, pk=bid_id, task=task)
        if bid.status == Bid.Status.ACCEPTED:
            raise ValidationError("Accepted bids cannot be rejected.")

        bid.status = Bid.Status.REJECTED
        bid.save(update_fields=["status"])
        return Response(BidSerializer(bid).data)


class MarkTaskCompleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied("Admin accounts cannot complete marketplace tasks.")
        task = get_object_or_404(
            Task.objects.select_related("client", "assigned_tasker", "transaction"),
            pk=task_id,
        )
        if task.assigned_tasker_id != request.user.id:
            raise PermissionDenied("Only the assigned tasker can mark work complete.")

        transaction_obj = getattr(task, "transaction", None)
        escrow_is_funded = transaction_obj and transaction_obj.status == Transaction.Status.ESCROWED
        if (
            transaction_obj
            and transaction_obj.status == Transaction.Status.PENDING_PAYMENT
            and transaction_obj.econfirm_transaction_id
        ):
            external_status = EconfirmClient().check_transaction_status(
                transaction_obj.econfirm_transaction_id
            )
            external_data = external_status.get("data", external_status) if external_status else {}
            external_state = str(external_data.get("status", "")).lower()
            external_event = str(external_data.get("event", external_status.get("event", "") if external_status else "")).lower()
            if external_state in {"funded", "in_progress", "held", "escrowed"} or external_event in {
                "payment.success",
                "escrow.funded",
                "funds.held",
            }:
                hold_funds(transaction_obj)
                task.refresh_from_db()
                transaction_obj.refresh_from_db()
                escrow_is_funded = True

        if task.status == Task.Status.ASSIGNED and escrow_is_funded:
            task.status = Task.Status.IN_PROGRESS
            task.save(update_fields=["status", "updated_at"])
        elif task.status != Task.Status.IN_PROGRESS:
            raise ValidationError(
                "Escrow funding has not synced yet. Tap Check Escrow or ask the client to confirm payment."
            )
        if task.tasker_completed_at:
            return Response(
                {
                    "message": "Completion is already waiting for client approval.",
                    "tasker_completed_at": task.tasker_completed_at,
                }
            )

        task.tasker_completed_at = timezone.now()
        task.save(update_fields=["tasker_completed_at", "updated_at"])

        send_notification(
            task.client,
            Notification.Type.TASK_COMPLETED,
            "Task ready for approval",
            f"{task.assigned_tasker.full_name} marked '{task.title}' as complete. Review the work and release escrow if everything looks good.",
            related_task=task,
        )

        return Response(
            {
                "message": "Your task has been marked complete. Please wait for client approval and funds release.",
                "client_message": "The tasker marked this task complete. Review the work and release escrow if everything looks good.",
                "tasker_completed_at": task.tasker_completed_at,
            }
        )


class ForgetTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        now = timezone.now()
        update_fields = ["updated_at"]

        if task.client_id == request.user.id:
            task.client_hidden_at = now
            update_fields.append("client_hidden_at")
        elif task.assigned_tasker_id == request.user.id:
            task.tasker_hidden_at = now
            update_fields.append("tasker_hidden_at")
        else:
            raise PermissionDenied("You can only forget your own posted or assigned tasks.")

        task.save(update_fields=update_fields)
        return Response({"message": "Task hidden from your list."})
