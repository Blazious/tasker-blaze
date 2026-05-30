from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Review(models.Model):
    class ReviewType(models.TextChoices):
        CLIENT_TO_TASKER = "CLIENT_TO_TASKER", "Client to Tasker"
        TASKER_TO_CLIENT = "TASKER_TO_CLIENT", "Tasker to Client"

    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_written",
    )
    reviewee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_received",
    )
    rating = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )
    communication_rating = models.IntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )
    punctuality_rating = models.IntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )
    quality_rating = models.IntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
    )
    comment = models.TextField(max_length=500)
    review_type = models.CharField(max_length=20, choices=ReviewType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    is_visible = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("task", "reviewer")

    def clean(self):
        super().clean()
        if self.task_id and self.task.status != "COMPLETED":
            raise ValidationError("Reviews can only be submitted for completed tasks.")
        if self.reviewer_id and self.reviewee_id and self.reviewer_id == self.reviewee_id:
            raise ValidationError("Users cannot review themselves.")

    def __str__(self):
        return f"{self.reviewer} reviewed {self.reviewee} for {self.task}"


class UserReport(models.Model):
    class Reason(models.TextChoices):
        HARASSMENT = "HARASSMENT", "Harassment or abusive behaviour"
        SAFETY_CONCERN = "SAFETY_CONCERN", "Safety concern"
        NO_SHOW = "NO_SHOW", "Did not show up"
        POOR_WORK = "POOR_WORK", "Poor or slow work"
        PAYMENT_ISSUE = "PAYMENT_ISSUE", "Payment issue"
        INAPPROPRIATE_CONTENT = "INAPPROPRIATE_CONTENT", "Inappropriate content"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        REVIEWING = "REVIEWING", "Reviewing"
        RESOLVED = "RESOLVED", "Resolved"
        DISMISSED = "DISMISSED", "Dismissed"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_submitted",
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reports_received",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_reports",
    )
    reason = models.CharField(max_length=40, choices=Reason.choices)
    details = models.TextField(max_length=1000)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Only publish after admin moderation.",
    )
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("reporter", "reported_user", "task", "reason")

    def clean(self):
        super().clean()
        if self.reporter_id and self.reported_user_id and self.reporter_id == self.reported_user_id:
            raise ValidationError("Users cannot report themselves.")

    def __str__(self):
        return f"{self.reporter} reported {self.reported_user} - {self.reason}"
