from django.contrib import admin

from .models import Bid, Task, TaskCategory


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon_name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description", "icon_name")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "client",
        "category",
        "budget_min",
        "budget_max",
        "location_landmark",
        "requires_home_visit",
        "preferred_tasker_gender",
        "schedule_type",
        "scheduled_for",
        "status",
        "assigned_tasker",
        "created_at",
        "deadline",
    )
    list_filter = (
        "status",
        "category",
        "location_landmark",
        "requires_home_visit",
        "preferred_tasker_gender",
        "schedule_type",
        "scheduled_for",
        "created_at",
        "deadline",
    )
    search_fields = (
        "title",
        "description",
        "client__email",
        "client__full_name",
        "assigned_tasker__email",
        "assigned_tasker__full_name",
        "location_notes",
    )
    readonly_fields = ("created_at", "updated_at", "assigned_at", "completed_at")


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("task", "tasker", "amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = (
        "task__title",
        "tasker__email",
        "tasker__full_name",
        "message",
    )
    readonly_fields = ("created_at",)
