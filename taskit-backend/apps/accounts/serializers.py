import cloudinary
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from rest_framework.exceptions import PermissionDenied
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import KYCVerification, validate_jkuat_student_email

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "password", "full_name", "phone_number", "gender")

    def validate_email(self, value):
        email = value.lower()
        validate_jkuat_student_email(email)
        return email

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        email = value.lower()
        validate_jkuat_student_email(email)
        return email

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"],
            password=attrs["password"],
        )

        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_verified:
            raise PermissionDenied("Please verify your JKUAT email first.")

        attrs["user"] = user
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone_number",
            "gender",
            "student_id",
            "department",
            "year_of_study",
            "profile_photo",
            "bio",
            "is_tasker_active",
            "availability_status",
            "availability_note",
            "available_until",
            "is_verified",
            "is_kyc_verified",
            "date_joined",
            "last_seen",
        )
        read_only_fields = (
            "id",
            "email",
            "is_verified",
            "is_kyc_verified",
            "date_joined",
            "last_seen",
        )

    def update(self, instance, validated_data):
        if (
            settings.DEBUG
            and validated_data.get("profile_photo")
            and not cloudinary.config().api_key
        ):
            validated_data.pop("profile_photo", None)
        return super().update(instance, validated_data)


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("availability_status", "availability_note", "available_until")

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.is_tasker_active:
            raise serializers.ValidationError(
                "Activate tasker mode before changing availability."
            )
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = RefreshToken(attrs["refresh"])
        return attrs

    def save(self, **kwargs):
        self.token.blacklist()


class RefreshTokenSerializer(TokenRefreshSerializer):
    pass


class KYCVerificationSerializer(serializers.ModelSerializer):
    prefill = serializers.SerializerMethodField()
    face_match_confidence_label = serializers.SerializerMethodField()
    verification_summary = serializers.SerializerMethodField()

    class Meta:
        model = KYCVerification
        fields = (
            "id",
            "status",
            "id_front_image",
            "id_back_image",
            "live_face_image",
            "extracted_full_name",
            "extracted_student_id",
            "extracted_date_of_birth",
            "extracted_issue_date",
            "extracted_expiration_date",
            "extracted_university_name",
            "extracted_department",
            "extracted_school",
            "extracted_degree",
            "extracted_validity_period",
            "stamp_detected",
            "id_photo_detected",
            "face_match_confidence",
            "face_match_confidence_label",
            "verification_summary",
            "reviewer_notes",
            "submitted_at",
            "processed_at",
            "reviewed_at",
            "prefill",
        )
        read_only_fields = (
            "id",
            "status",
            "extracted_full_name",
            "extracted_student_id",
            "extracted_date_of_birth",
            "extracted_issue_date",
            "extracted_expiration_date",
            "extracted_university_name",
            "extracted_department",
            "extracted_school",
            "extracted_degree",
            "extracted_validity_period",
            "stamp_detected",
            "id_photo_detected",
            "face_match_confidence",
            "face_match_confidence_label",
            "verification_summary",
            "reviewer_notes",
            "submitted_at",
            "processed_at",
            "reviewed_at",
            "prefill",
        )
        extra_kwargs = {
            "id_front_image": {"write_only": True},
            "id_back_image": {"write_only": True, "required": False},
            "live_face_image": {"write_only": True, "required": False},
        }

    def get_prefill(self, obj):
        return {
            "full_name": obj.extracted_full_name,
            "student_id": obj.extracted_student_id,
            "department": obj.extracted_department or obj.extracted_school or obj.extracted_degree,
            "degree": obj.extracted_degree,
        }

    def get_face_match_confidence_label(self, obj):
        return obj.face_match_raw_response.get("confidence_label", "") if obj.face_match_raw_response else ""

    def get_verification_summary(self, obj):
        return {
            "ocr_provider": obj.ocr_raw_response.get("provider", "mock") if obj.ocr_raw_response else "",
            "has_identity_fields": bool(obj.extracted_full_name or obj.extracted_student_id),
            "has_jkuat_evidence": obj.stamp_detected or "jkuat" in (obj.extracted_university_name or "").lower(),
            "face_match": obj.face_match_raw_response.get("match") if obj.face_match_raw_response else None,
            "ready_for_review": obj.status == KYCVerification.Status.PENDING_REVIEW,
        }

    def validate(self, attrs):
        if self.context.get("request") and self.context["request"].method == "POST":
            if not attrs.get("id_front_image"):
                raise serializers.ValidationError({"id_front_image": "Front of student ID is required."})
        return attrs
