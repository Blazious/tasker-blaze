from django.contrib import admin

from .models import Review, UserReport


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "task",
        "reviewer",
        "reviewee",
        "rating",
        "review_type",
        "is_visible",
        "created_at",
    )
    list_filter = ("review_type", "rating", "is_visible", "created_at")
    search_fields = (
        "task__title",
        "reviewer__email",
        "reviewer__full_name",
        "reviewee__email",
        "reviewee__full_name",
        "comment",
    )
    readonly_fields = ("created_at",)


@admin.register(UserReport)
class UserReportAdmin(admin.ModelAdmin):
    list_display = (
        "reported_user",
        "reporter",
        "reason",
        "status",
        "is_public",
        "task",
        "created_at",
    )
    list_filter = ("reason", "status", "is_public", "created_at")
    search_fields = (
        "reported_user__email",
        "reported_user__full_name",
        "reporter__email",
        "reporter__full_name",
        "task__title",
        "details",
        "admin_notes",
    )
    readonly_fields = ("created_at", "updated_at")
