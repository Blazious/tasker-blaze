from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tasks.models import Task

from .models import Review, UserReport
from .serializers import PublicProfileSerializer, ReviewSerializer, UserReportSerializer
from .utils import reveal_reviews_if_pair_complete

User = get_user_model()


class ReviewsHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"app": "reviews", "status": "ok"})


class SubmitReviewView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, task_id):
        task = get_object_or_404(
            Task.objects.select_related("client", "assigned_tasker"),
            pk=task_id,
        )
        if task.status != Task.Status.COMPLETED:
            raise ValidationError("Reviews can only be submitted for completed tasks.")
        if not task.assigned_tasker_id:
            raise ValidationError("This task has no assigned tasker to review.")

        if request.user.id == task.client_id:
            reviewee = task.assigned_tasker
            review_type = Review.ReviewType.CLIENT_TO_TASKER
        elif request.user.id == task.assigned_tasker_id:
            reviewee = task.client
            review_type = Review.ReviewType.TASKER_TO_CLIENT
        else:
            raise PermissionDenied("Only the task client or tasker can review this task.")

        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            review = Review.objects.create(
                task=task,
                reviewer=request.user,
                reviewee=reviewee,
                review_type=review_type,
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data["comment"],
            )
            review.full_clean()
        except IntegrityError as exc:
            raise ValidationError("You have already reviewed this task.") from exc

        reveal_reviews_if_pair_complete(task)
        review.refresh_from_db()
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class UserReviewsView(generics.ListAPIView):
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user = get_object_or_404(User, pk=self.kwargs["user_id"])
        return Review.objects.filter(reviewee=user, is_visible=True).select_related(
            "task",
            "reviewer",
            "reviewee",
        )


class ReportUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        reported_user = get_object_or_404(User, pk=user_id)
        if reported_user.id == request.user.id:
            raise ValidationError("You cannot report yourself.")

        serializer = UserReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task = serializer.validated_data.get("task")
        if task:
            is_participant = (
                task.client_id == request.user.id
                or task.assigned_tasker_id == request.user.id
                or task.bids.filter(tasker=request.user).exists()
            )
            if not is_participant:
                raise PermissionDenied("You can only attach reports to tasks you participated in.")
            reported_is_participant = (
                task.client_id == reported_user.id
                or task.assigned_tasker_id == reported_user.id
                or task.bids.filter(tasker=reported_user).exists()
            )
            if not reported_is_participant:
                raise ValidationError("The reported user is not linked to this task.")

        try:
            report = serializer.save(
                reporter=request.user,
                reported_user=reported_user,
            )
        except IntegrityError as exc:
            raise ValidationError("You have already submitted this report.") from exc

        return Response(UserReportSerializer(report).data, status=status.HTTP_201_CREATED)


class PublicProfileView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        return Response(PublicProfileSerializer(user).data)
