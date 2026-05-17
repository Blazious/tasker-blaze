from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "notification_type",
        "title",
        "related_task",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("recipient__email", "recipient__full_name", "title", "body")
    readonly_fields = ("created_at",)
