from rest_framework import serializers

from .badges import get_badges
from .models import Review, UserReport


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source="reviewer.full_name", read_only=True)
    reviewee_name = serializers.CharField(source="reviewee.full_name", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = Review
        fields = (
            "id",
            "task",
            "task_title",
            "reviewer",
            "reviewer_name",
            "reviewee",
            "reviewee_name",
            "rating",
            "comment",
            "review_type",
            "created_at",
            "is_visible",
        )
        read_only_fields = (
            "id",
            "task",
            "task_title",
            "reviewer",
            "reviewer_name",
            "reviewee",
            "reviewee_name",
            "review_type",
            "created_at",
            "is_visible",
        )

    def validate_comment(self, value):
        if not value.strip():
            raise serializers.ValidationError("Comment is required.")
        return value


class PublicProfileSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    profile_photo = serializers.SerializerMethodField()
    bio = serializers.CharField()
    department = serializers.CharField()
    year_of_study = serializers.IntegerField(allow_null=True)
    is_tasker_active = serializers.BooleanField()
    availability_status = serializers.CharField()
    availability_note = serializers.CharField()
    available_until = serializers.DateTimeField(allow_null=True)
    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    completed_tasks_count = serializers.IntegerField()
    badges = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    completed_task_history = serializers.SerializerMethodField()
    public_report_count = serializers.SerializerMethodField()
    public_reports = serializers.SerializerMethodField()

    def get_profile_photo(self, obj):
        return str(obj.profile_photo) if obj.profile_photo else ""

    def get_badges(self, obj):
        return get_badges(obj)

    def get_recent_reviews(self, obj):
        reviews = Review.objects.filter(reviewee=obj, is_visible=True).select_related(
            "task",
            "reviewer",
            "reviewee",
        )[:5]
        return ReviewSerializer(reviews, many=True).data

    def get_completed_task_history(self, obj):
        tasks = obj.assigned_tasks.filter(status="COMPLETED").select_related(
            "category",
            "client",
        )[:5]
        return [
            {
                "id": task.id,
                "title": task.title,
                "category": task.category.name,
                "client_name": task.client.full_name,
                "completed_at": task.completed_at,
            }
            for task in tasks
        ]

    def get_public_report_count(self, obj):
        return UserReport.objects.filter(reported_user=obj, is_public=True).count()

    def get_public_reports(self, obj):
        reports = UserReport.objects.filter(
            reported_user=obj,
            is_public=True,
        ).select_related("reporter", "reported_user", "task")[:5]
        return UserReportSerializer(reports, many=True).data


class UserReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source="reporter.full_name", read_only=True)
    reported_user_name = serializers.CharField(source="reported_user.full_name", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)

    class Meta:
        model = UserReport
        fields = (
            "id",
            "reporter",
            "reporter_name",
            "reported_user",
            "reported_user_name",
            "task",
            "task_title",
            "reason",
            "details",
            "status",
            "is_public",
            "created_at",
        )
        read_only_fields = (
            "id",
            "reporter",
            "reporter_name",
            "reported_user",
            "reported_user_name",
            "status",
            "is_public",
            "created_at",
        )

    def validate_details(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Please add at least 10 characters of detail.")
        return value.strip()
