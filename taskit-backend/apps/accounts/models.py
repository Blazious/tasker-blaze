from cloudinary.models import CloudinaryField
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


JKUAT_STUDENT_EMAIL_DOMAIN = "@students.jkuat.ac.ke"


def validate_jkuat_student_email(email):
    if not email or not email.lower().endswith(JKUAT_STUDENT_EMAIL_DOMAIN):
        raise ValidationError("Only JKUAT student emails are allowed.")


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email field must be set.")

        email = self.normalize_email(email).lower()
        validate_jkuat_student_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.full_clean()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Gender(models.TextChoices):
        NOT_SPECIFIED = "NOT_SPECIFIED", "Prefer not to say"
        FEMALE = "FEMALE", "Female"
        MALE = "MALE", "Male"
        OTHER = "OTHER", "Other"

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        BUSY = "BUSY", "Busy"
        OFFLINE = "OFFLINE", "Offline"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=32)
    gender = models.CharField(
        max_length=20,
        choices=Gender.choices,
        default=Gender.NOT_SPECIFIED,
    )
    student_id = models.CharField(max_length=64, blank=True)
    department = models.CharField(max_length=255, blank=True)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)
    profile_photo = CloudinaryField("profile_photo", blank=True, null=True)
    bio = models.TextField(blank=True)
    is_tasker_active = models.BooleanField(default=False)
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.OFFLINE,
    )
    availability_note = models.CharField(max_length=255, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_kyc_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "phone_number"]

    class Meta:
        ordering = ["-date_joined"]

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email).lower()
        validate_jkuat_student_email(self.email)

        if self.year_of_study is not None and self.year_of_study not in range(1, 5):
            raise ValidationError(
                {"year_of_study": "Year of study must be between 1 and 4."}
            )

    def __str__(self):
        return self.email

    @property
    def average_rating(self):
        from apps.reviews.utils import get_average_rating

        return get_average_rating(self)

    @property
    def total_reviews(self):
        from apps.reviews.utils import get_total_reviews

        return get_total_reviews(self)

    @property
    def completed_tasks_count(self):
        from apps.reviews.utils import get_completed_tasks_count

        return get_completed_tasks_count(self)


class KYCVerification(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "NOT_STARTED", "Not Started"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        NEEDS_RETRY = "NEEDS_RETRY", "Needs Retry"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="kyc_verification",
    )
    id_front_image = models.ImageField(upload_to="kyc/id_fronts/")
    id_back_image = models.ImageField(upload_to="kyc/id_backs/")
    live_face_image = models.ImageField(upload_to="kyc/live_faces/", blank=True, null=True)
    extracted_full_name = models.CharField(max_length=255, blank=True)
    extracted_student_id = models.CharField(max_length=64, blank=True)
    extracted_date_of_birth = models.CharField(max_length=32, blank=True)
    extracted_issue_date = models.CharField(max_length=32, blank=True)
    extracted_expiration_date = models.CharField(max_length=32, blank=True)
    extracted_university_name = models.CharField(max_length=255, blank=True)
    extracted_department = models.CharField(max_length=255, blank=True)
    extracted_school = models.CharField(max_length=255, blank=True)
    extracted_degree = models.CharField(max_length=255, blank=True)
    extracted_validity_period = models.CharField(max_length=64, blank=True)
    stamp_detected = models.BooleanField(default=False)
    id_photo_detected = models.BooleanField(default=False)
    face_match_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Confidence percentage from 0.00 to 100.00.",
    )
    ocr_raw_response = models.JSONField(default=dict, blank=True)
    face_match_raw_response = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_REVIEW,
    )
    reviewer_notes = models.TextField(blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"KYC for {self.user.email} - {self.status}"

    @property
    def can_prefill_profile(self):
        return self.status in {
            self.Status.PENDING_REVIEW,
            self.Status.APPROVED,
        }
