from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .kyc import normalize_jkuat_college
from .models import KYCVerification, validate_jkuat_student_email


def tiny_gif(name):
    return SimpleUploadedFile(
        name,
        b"GIF87a\x01\x00\x01\x00\x80\x01\x00\x00\x00\x00ccc,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;",
        content_type="image/gif",
    )


class KYCVerificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="kyc.user@students.jkuat.ac.ke",
            password="Testpass123!",
            full_name="KYC User",
            phone_number="+254700000010",
            student_id="SCT211-0001/2024",
            department="Computer Science",
            is_verified=True,
        )
        self.api_client = APIClient()
        self.api_client.force_authenticate(self.user)

    @override_settings(KYC_MOCK=True)
    def test_kyc_submission_returns_summary_and_prefill(self):
        response = self.api_client.post(
            "/api/v1/auth/kyc/",
            {
                "id_front_image": tiny_gif("front.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], KYCVerification.Status.PENDING_REVIEW)
        self.assertTrue(response.data["verification_summary"]["has_identity_fields"])
        self.assertTrue(response.data["verification_summary"]["has_jkuat_evidence"])
        self.assertEqual(response.data["prefill"]["student_id"], self.user.student_id)

    @override_settings(KYC_MOCK=False, KYC_FACE_MATCH_THRESHOLD=75)
    @patch("apps.accounts.kyc.run_mindee_ocr")
    @patch("apps.accounts.kyc.run_face_match")
    def test_low_face_match_sets_face_mismatch_status(self, mock_face, mock_ocr):
        mock_ocr.return_value = {
            "full_name": "KYC User",
            "student_id": "SCT211-0001/2024",
            "department": "Computer Science",
            "school": "",
            "degree": "",
            "stamp_detected": True,
            "id_photo_detected": True,
            "raw": {"provider": "test"},
        }
        mock_face.return_value = {
            "confidence": 42,
            "match": False,
            "confidence_label": "Low",
            "raw": {"mode": "test"},
        }

        response = self.api_client.post(
            "/api/v1/auth/kyc/",
            {
                "id_front_image": tiny_gif("front.gif"),
                "live_face_image": tiny_gif("face.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], KYCVerification.Status.FACE_MISMATCH)
        self.assertEqual(response.data["face_match_confidence_label"], "Low")
        self.assertFalse(response.data["verification_summary"]["face_match"])

    @override_settings(KYC_MOCK=False, KYC_FACE_MATCH_THRESHOLD=75)
    @patch("apps.accounts.kyc.run_mindee_ocr")
    @patch("apps.accounts.kyc.run_face_match")
    def test_face_match_still_runs_when_ocr_fails(self, mock_face, mock_ocr):
        mock_ocr.side_effect = ValueError("Mindee is not configured")
        mock_face.return_value = {
            "confidence": 88,
            "match": True,
            "confidence_label": "High",
            "raw": {"mode": "test"},
        }

        response = self.api_client.post(
            "/api/v1/auth/kyc/",
            {
                "id_front_image": tiny_gif("front.gif"),
                "live_face_image": tiny_gif("face.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], KYCVerification.Status.NEEDS_RETRY)
        self.assertEqual(response.data["face_match_confidence"], "88.00")
        self.assertEqual(response.data["face_match_confidence_label"], "High")
        self.assertTrue(response.data["verification_summary"]["face_match"])

    @override_settings(
        KYC_MOCK=False,
        KYC_ENABLE_LOCAL_OCR=False,
        KYC_ENABLE_FACE_MATCH=False,
        MINDEE_API_KEY="",
        MINDEE_MODEL_ID="",
        MINDEE_ENDPOINT_URL="",
    )
    def test_kyc_without_external_processors_goes_to_manual_review(self):
        response = self.api_client.post(
            "/api/v1/auth/kyc/",
            {
                "id_front_image": tiny_gif("front.gif"),
                "live_face_image": tiny_gif("face.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], KYCVerification.Status.PENDING_REVIEW)
        self.assertEqual(response.data["verification_summary"]["ocr_provider"], "manual_review")
        self.assertIsNone(response.data["verification_summary"]["face_match"])

    @override_settings(KYC_MOCK=False, MINDEE_API_KEY="test-key", MINDEE_MODEL_ID="test-model")
    @patch("apps.accounts.kyc.run_mindee_model_ocr")
    def test_mindee_model_id_path_is_used_when_configured(self, mock_model_ocr):
        mock_model_ocr.return_value = {
            "full_name": "KYC User",
            "student_id": "SCT211-0001/2024",
            "department": "Computer Science",
            "school": "",
            "degree": "",
            "stamp_detected": True,
            "id_photo_detected": True,
            "raw": {"provider": "mindee_model"},
        }

        response = self.api_client.post(
            "/api/v1/auth/kyc/",
            {
                "id_front_image": tiny_gif("front.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        mock_model_ocr.assert_called_once()
        self.assertEqual(response.data["status"], KYCVerification.Status.PENDING_REVIEW)
        self.assertEqual(response.data["verification_summary"]["ocr_provider"], "mindee_model")

    def test_jkuat_college_acronyms_are_normalized(self):
        self.assertEqual(normalize_jkuat_college("CoHRED"), "College of Human Resource Development")
        self.assertEqual(normalize_jkuat_college("COPAS"), "College of Pure and Applied Sciences")

    def test_admin_can_list_kyc_submissions(self):
        admin = get_user_model().objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        KYCVerification.objects.create(
            user=self.user,
            id_front_image=tiny_gif("front.gif"),
            status=KYCVerification.Status.PENDING_REVIEW,
            extracted_full_name="KYC User",
            extracted_student_id="SCT211-0001/2024",
            stamp_detected=True,
        )
        api_client = APIClient()
        api_client.force_authenticate(admin)

        response = api_client.get("/api/v1/auth/admin/kyc/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"]["email"], self.user.email)
        self.assertEqual(response.data[0]["status"], KYCVerification.Status.PENDING_REVIEW)

    def test_admin_approval_marks_user_kyc_verified(self):
        admin = get_user_model().objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        kyc = KYCVerification.objects.create(
            user=self.user,
            id_front_image=tiny_gif("front.gif"),
            status=KYCVerification.Status.PENDING_REVIEW,
        )
        api_client = APIClient()
        api_client.force_authenticate(admin)

        response = api_client.patch(
            f"/api/v1/auth/admin/kyc/{kyc.id}/",
            {
                "status": KYCVerification.Status.APPROVED,
                "reviewer_notes": "Student ID matches profile.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        kyc.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(kyc.status, KYCVerification.Status.APPROVED)
        self.assertEqual(kyc.reviewer_notes, "Student ID matches profile.")
        self.assertIsNotNone(kyc.reviewed_at)
        self.assertTrue(self.user.is_kyc_verified)

    def test_admin_rejection_marks_user_kyc_unverified(self):
        admin = get_user_model().objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        self.user.is_kyc_verified = True
        self.user.save(update_fields=["is_kyc_verified"])
        kyc = KYCVerification.objects.create(
            user=self.user,
            id_front_image=tiny_gif("front.gif"),
            status=KYCVerification.Status.APPROVED,
        )
        api_client = APIClient()
        api_client.force_authenticate(admin)

        response = api_client.patch(
            f"/api/v1/auth/admin/kyc/{kyc.id}/",
            {"status": KYCVerification.Status.REJECTED},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_kyc_verified)


class StudentEmailAccessTests(TestCase):
    def test_rejects_non_jkuat_student_domains(self):
        with self.assertRaises(ValidationError):
            validate_jkuat_student_email("student@gmail.com")

    def test_rejects_reserved_dummy_local_parts(self):
        with self.assertRaises(ValidationError):
            validate_jkuat_student_email("test@students.jkuat.ac.ke")

    def test_accepts_personal_jkuat_student_domain(self):
        validate_jkuat_student_email("cliptoman@students.jkuat.ac.ke")

    @override_settings(ADMIN_EMAIL="admintaskit@gmail.com")
    def test_admin_email_can_login_when_created_as_superuser(self):
        User = get_user_model()
        User.objects.create_superuser(
            email="admintaskit@gmail.com",
            password="Adminpass123!",
            full_name="TaskiT Admin",
            phone_number="+254700000000",
        )
        api_client = APIClient()

        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "admintaskit@gmail.com", "password": "Adminpass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        profile_response = api_client.get("/api/v1/auth/me/")
        self.assertTrue(profile_response.data["is_staff"])
        self.assertTrue(profile_response.data["is_superuser"])

    @override_settings(ADMIN_EMAIL="admintaskit@gmail.com")
    def test_admin_email_cannot_self_register_publicly(self):
        api_client = APIClient()

        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "admintaskit@gmail.com",
                "password": "Adminpass123!",
                "full_name": "TaskiT Admin",
                "phone_number": "+254700000000",
                "gender": "NOT_SPECIFIED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    @override_settings(EMAIL_VERIFICATION_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_registration_requires_email_verification_by_default(self):
        api_client = APIClient()

        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "fresh.student@students.jkuat.ac.ke",
                "password": "Testpass123!",
                "full_name": "Fresh Student",
                "phone_number": "+254700000011",
                "gender": "NOT_SPECIFIED",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = get_user_model().objects.get(email="fresh.student@students.jkuat.ac.ke")
        self.assertFalse(user.is_verified)
        self.assertTrue(response.data["email_verification_required"])
