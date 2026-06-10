import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Sum
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAdminUser

from .serializers import (
    AdminKYCVerificationSerializer,
    AvailabilitySerializer,
    KYCVerificationSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserProfileSerializer,
)
from .kyc import normalize_jkuat_college, process_kyc
from .models import KYCVerification

User = get_user_model()
EMAIL_VERIFICATION_SALT = "accounts.email-verification"
EMAIL_VERIFICATION_MAX_AGE = 60 * 60 * 24
logger = logging.getLogger(__name__)


class AccountsHealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response({"app": "accounts", "status": "ok"})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if not settings.EMAIL_VERIFICATION_ENABLED:
            user.is_verified = True
            user.save(update_fields=["is_verified"])
            return Response(
                {
                    "message": "Account created successfully. You can log in now.",
                    "email_verification_required": False,
                },
                status=status.HTTP_201_CREATED,
            )

        try:
            self.send_verification_email(request, user)
        except Exception:
            logger.exception("Failed to send verification email to %s", user.email)
            user.delete()
            return Response(
                {
                    "detail": (
                        "We could not send the verification email right now. "
                        "Please try again in a few minutes."
                    ),
                    "email_verification_required": True,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "message": "Check your email to verify your account.",
                "email_verification_required": True,
            },
            status=status.HTTP_201_CREATED,
        )

    def send_verification_email(self, request, user):
        token = signing.dumps({"user_id": user.pk}, salt=EMAIL_VERIFICATION_SALT)
        verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
        send_mail(
            subject="Verify your Taskit account",
            message=(
                "Welcome to Taskit.\n\n"
                f"Verify your email here: {verification_url}\n\n"
                "This link expires in 24 hours."
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[user.email],
            fail_silently=False,
        )


class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"detail": "Verification token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = signing.loads(
                token,
                salt=EMAIL_VERIFICATION_SALT,
                max_age=EMAIL_VERIFICATION_MAX_AGE,
            )
        except signing.SignatureExpired:
            return Response(
                {"detail": "Verification token has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except signing.BadSignature:
            return Response(
                {"detail": "Invalid verification token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(User, pk=payload["user_id"])
        user.is_verified = True
        user.save(update_fields=["is_verified"])

        return Response({"message": "Email verified successfully."})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        refresh = RefreshToken.for_user(serializer.validated_data["user"])

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ActivateTaskerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied("Admin accounts cannot activate tasker mode.")
        request.user.is_tasker_active = True
        if request.user.availability_status == User.AvailabilityStatus.OFFLINE:
            request.user.availability_status = User.AvailabilityStatus.AVAILABLE
        request.user.save(update_fields=["is_tasker_active", "availability_status"])
        return Response({"message": "Tasker mode activated."})


class AvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = AvailabilitySerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(request.user).data)


class AvailableTaskersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        taskers = User.objects.filter(
            is_tasker_active=True,
            is_verified=True,
            availability_status=User.AvailabilityStatus.AVAILABLE,
        ).order_by("full_name")[:50]
        return Response(UserProfileSerializer(taskers, many=True).data)


class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.payments.models import Transaction
        from apps.tasks.models import Bid, Task

        total_earned = (
            Transaction.objects.filter(
                tasker=request.user,
                status=Transaction.Status.RELEASED,
            ).aggregate(total=Sum("tasker_payout"))["total"]
            or 0
        )

        return Response(
            {
                "tasks_posted": Task.objects.filter(client=request.user).count(),
                "tasks_completed": Task.objects.filter(
                    assigned_tasker=request.user,
                    status=Task.Status.COMPLETED,
                ).count(),
                "active_bids": Bid.objects.filter(
                    tasker=request.user,
                    status=Bid.Status.PENDING,
                ).count(),
                "total_earned": str(total_earned),
            }
        )


class KYCVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        kyc = getattr(request.user, "kyc_verification", None)
        if not kyc:
            return Response(
                {
                    "status": KYCVerification.Status.NOT_STARTED,
                    "prefill": {},
                }
            )
        return Response(KYCVerificationSerializer(kyc).data)

    def post(self, request):
        existing = getattr(request.user, "kyc_verification", None)
        serializer = KYCVerificationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        if existing:
            existing.delete()

        kyc = serializer.save(user=request.user)
        process_kyc(kyc)

        return Response(
            KYCVerificationSerializer(kyc).data,
            status=status.HTTP_201_CREATED,
        )


class AdminKYCVerificationListView(generics.ListAPIView):
    serializer_class = AdminKYCVerificationSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = KYCVerification.objects.select_related("user")
        status_filter = self.request.query_params.get("status")

        if status_filter and status_filter != "ALL":
            queryset = queryset.filter(status=status_filter)

        return queryset


class AdminKYCVerificationDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = AdminKYCVerificationSerializer
    permission_classes = [IsAdminUser]
    queryset = KYCVerification.objects.select_related("user")
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        kyc = serializer.save(reviewed_at=timezone.now())
        user = kyc.user
        user.is_kyc_verified = kyc.status == KYCVerification.Status.APPROVED
        user.save(update_fields=["is_kyc_verified"])


class KYCPrefillProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        kyc = get_object_or_404(KYCVerification, user=request.user)
        if not kyc.can_prefill_profile:
            return Response(
                {"detail": "KYC details are not ready for profile prefill."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        if kyc.extracted_full_name:
            user.full_name = kyc.extracted_full_name
        if kyc.extracted_student_id:
            user.student_id = kyc.extracted_student_id
        if kyc.extracted_department or kyc.extracted_school:
            user.department = kyc.extracted_department or normalize_jkuat_college(kyc.extracted_school)

        user.save(update_fields=["full_name", "student_id", "department"])
        return Response(UserProfileSerializer(user).data)
