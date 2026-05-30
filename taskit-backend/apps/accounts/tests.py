from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import KYCVerification


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
                "id_back_image": tiny_gif("back.gif"),
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
                "id_back_image": tiny_gif("back.gif"),
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
                "id_back_image": tiny_gif("back.gif"),
                "live_face_image": tiny_gif("face.gif"),
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], KYCVerification.Status.NEEDS_RETRY)
        self.assertEqual(response.data["face_match_confidence"], "88.00")
        self.assertEqual(response.data["face_match_confidence_label"], "High")
        self.assertTrue(response.data["verification_summary"]["face_match"])
