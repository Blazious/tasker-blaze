from cloudinary.models import CloudinaryField
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .constants import JKUAT_LANDMARK_CHOICES


class TaskCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    icon_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "task categories"

    def __str__(self):
        return self.name


class Task(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        DISPUTED = "DISPUTED", "Disputed"

    class TaskerGenderPreference(models.TextChoices):
        ANY = "ANY", "Any"
        FEMALE = "FEMALE", "Female"
        MALE = "MALE", "Male"

    class ScheduleType(models.TextChoices):
        ASAP = "ASAP", "As soon as possible"
        SCHEDULED = "SCHEDULED", "Scheduled"

    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posted_tasks",
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(
        TaskCategory,
        on_delete=models.PROTECT,
        related_name="tasks",
    )
    budget_min = models.DecimalField(max_digits=10, decimal_places=2)
    budget_max = models.DecimalField(max_digits=10, decimal_places=2)
    location_landmark = models.CharField(max_length=100, choices=JKUAT_LANDMARK_CHOICES)
    location_notes = models.CharField(max_length=255, blank=True)
    location_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    location_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    task_photo = CloudinaryField("task_photo", blank=True, null=True)
    requires_home_visit = models.BooleanField(default=False)
    preferred_tasker_gender = models.CharField(
        max_length=10,
        choices=TaskerGenderPreference.choices,
        default=TaskerGenderPreference.ANY,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    tasker_completed_at = models.DateTimeField(null=True, blank=True)
    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices,
        default=ScheduleType.ASAP,
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_open(self):
        return self.status == self.Status.OPEN

    def clean(self):
        super().clean()
        if self.client_id and not self.client.is_verified:
            raise ValidationError({"client": "Only verified users can post tasks."})
        if self.budget_min is not None and self.budget_max is not None:
            if self.budget_min > self.budget_max:
                raise ValidationError(
                    {"budget_max": "Maximum budget must be greater than minimum budget."}
                )
        if (
            self.location_landmark == "Other (specify in notes)"
            and not self.location_notes
        ):
            raise ValidationError(
                {"location_notes": "Please specify the location in notes."}
            )
        if self.schedule_type == self.ScheduleType.SCHEDULED:
            if not self.scheduled_for:
                raise ValidationError(
                    {"scheduled_for": "Choose when this scheduled task should start."}
                )
            if self.scheduled_for <= timezone.now():
                raise ValidationError(
                    {"scheduled_for": "Scheduled tasks must be set for a future time."}
                )
        if self.deadline and self.scheduled_for and self.deadline < self.scheduled_for:
            raise ValidationError(
                {"deadline": "Deadline cannot be before the scheduled start time."}
            )

    def __str__(self):
        return self.title


class Bid(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="bids")
    tasker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bids",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("task", "tasker")

    def clean(self):
        super().clean()
        if self.task_id and self.tasker_id:
            if self.task.client_id == self.tasker_id:
                raise ValidationError("A tasker cannot bid on their own task.")
            if self.task.status != Task.Status.OPEN:
                raise ValidationError("Bids can only be placed on open tasks.")

    def __str__(self):
        return f"{self.tasker} bid on {self.task}"
