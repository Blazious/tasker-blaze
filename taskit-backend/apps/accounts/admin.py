from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import KYCVerification, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = (
        "email",
        "full_name",
        "phone_number",
        "gender",
        "department",
        "year_of_study",
        "is_tasker_active",
        "availability_status",
        "is_verified",
        "is_staff",
        "date_joined",
        "last_seen",
    )
    list_filter = (
        "is_tasker_active",
        "availability_status",
        "is_verified",
        "is_staff",
        "is_superuser",
        "year_of_study",
        "department",
    )
    search_fields = ("email", "full_name", "phone_number", "student_id")
    ordering = ("-date_joined",)
    readonly_fields = ("date_joined", "last_seen")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "password",
                    "full_name",
                    "phone_number",
                    "gender",
                    "student_id",
                    "department",
                    "year_of_study",
                    "profile_photo",
                    "bio",
                    "availability_status",
                    "availability_note",
                    "available_until",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_tasker_active",
                    "is_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "date_joined",
                    "last_seen",
                )
            },
        ),
        ("Permissions", {"fields": ("groups", "user_permissions")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "phone_number",
                    "password1",
                    "password2",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


@admin.register(KYCVerification)
class KYCVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "status",
        "extracted_full_name",
        "extracted_student_id",
        "stamp_detected",
        "id_photo_detected",
        "face_match_confidence",
        "submitted_at",
    )
    list_filter = ("status", "stamp_detected", "id_photo_detected", "submitted_at")
    search_fields = (
        "user__email",
        "user__full_name",
        "extracted_full_name",
        "extracted_student_id",
        "extracted_department",
        "extracted_school",
        "extracted_degree",
    )
    readonly_fields = (
        "ocr_raw_response",
        "face_match_raw_response",
        "submitted_at",
        "processed_at",
        "reviewed_at",
        "created_at",
        "updated_at",
    )

    def save_model(self, request, obj, form, change):
        from django.utils import timezone

        if "status" in form.changed_data:
            obj.reviewed_at = timezone.now()
            obj.user.is_kyc_verified = obj.status == KYCVerification.Status.APPROVED
            obj.user.save(update_fields=["is_kyc_verified"])
        super().save_model(request, obj, form, change)
