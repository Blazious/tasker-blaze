from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    related_task_title = serializers.CharField(source="related_task.title", read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "body",
            "related_task",
            "related_task_title",
            "is_read",
            "created_at",
        )
        read_only_fields = fields
