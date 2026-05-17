import logging
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

from .models import KYCVerification

logger = logging.getLogger(__name__)


def _extract_text_prediction(raw_response):
    document = raw_response.get("document", {})
    inference = document.get("inference", {})
    prediction = inference.get("prediction", {})
    flattened = {}

    for key, value in prediction.items():
        if isinstance(value, dict):
            if "value" in value or "raw_value" in value:
                flattened[key] = value.get("value") or value.get("raw_value") or ""
            elif "values" in value:
                flattened[key] = value.get("values") or []
            else:
                flattened[key] = value
        else:
            flattened[key] = value

    return flattened


def _first_present(data, *keys):
    for key in keys:
        value = data.get(key)
        if value:
            return value
    return ""


def _has_object_detection(data, *keys):
    for key in keys:
        value = data.get(key)
        if isinstance(value, list) and len(value) > 0:
            return True
        if isinstance(value, dict):
            if value.get("value") or value.get("values"):
                return True
        if value:
            return True
    return False


def run_mindee_ocr(kyc):
    if getattr(settings, "KYC_MOCK", True):
        return {
            "full_name": kyc.user.full_name,
            "student_id": kyc.user.student_id or "",
            "department": kyc.user.department or "",
            "school": "",
            "degree": "",
            "stamp_detected": True,
            "id_photo_detected": True,
            "raw": {"mode": "mock"},
        }

    api_key = getattr(settings, "MINDEE_API_KEY", "")
    endpoint = getattr(settings, "MINDEE_ENDPOINT_URL", "")
    if not api_key or not endpoint:
        raise ValueError("Mindee OCR is enabled but MINDEE_API_KEY or MINDEE_ENDPOINT_URL is missing.")

    headers = {"Authorization": f"Token {api_key}"}
    with kyc.id_front_image.open("rb") as front_file:
        front_response = requests.post(
            endpoint,
            headers=headers,
            files={"document": front_file},
            timeout=getattr(settings, "KYC_HTTP_TIMEOUT", 30),
        )
    front_response.raise_for_status()
    front_raw = front_response.json()
    front_prediction = _extract_text_prediction(front_raw)

    with kyc.id_back_image.open("rb") as back_file:
        back_response = requests.post(
            endpoint,
            headers=headers,
            files={"document": back_file},
            timeout=getattr(settings, "KYC_HTTP_TIMEOUT", 30),
        )
    back_response.raise_for_status()
    back_raw = back_response.json()
    back_text = str(back_raw).lower()

    return {
        "full_name": _first_present(front_prediction, "student_name", "full_name", "name"),
        "student_id": _first_present(front_prediction, "student_id", "registration_number", "reg_number"),
        "date_of_birth": _first_present(front_prediction, "date_of_birth", "dob"),
        "issue_date": _first_present(front_prediction, "issue_date", "issued_date"),
        "expiration_date": _first_present(front_prediction, "expiration_date", "expiry_date", "expiry"),
        "university_name": _first_present(front_prediction, "university_name", "institution_name"),
        "department": _first_present(front_prediction, "department"),
        "school": _first_present(front_prediction, "school", "faculty", "university_name"),
        "degree": _first_present(front_prediction, "degree", "program", "course"),
        "validity_period": _first_present(front_prediction, "validity_period"),
        "stamp_detected": "jkuat" in back_text or "jomo kenyatta university" in back_text,
        "id_photo_detected": _has_object_detection(front_prediction, "student_photo", "photo", "passport_photo"),
        "raw": {"front": front_raw, "back": back_raw},
    }


def run_face_match(kyc):
    if not kyc.live_face_image:
        return {"confidence": None, "raw": {"skipped": "No live face image supplied."}}

    if getattr(settings, "KYC_MOCK", True):
        return {"confidence": Decimal("88.00"), "raw": {"mode": "mock"}}

    try:
        from insightface.app import FaceAnalysis
    except ImportError as exc:
        raise ValueError("InsightFace is enabled but not installed.") from exc

    # Production note: the ID-card portrait extraction should crop the face from the
    # document image before comparison. For MVP, this analyzes the full front image
    # and live capture and compares the first detected face in each.
    import cv2
    import numpy as np

    app = FaceAnalysis(name=getattr(settings, "INSIGHTFACE_MODEL_NAME", "buffalo_l"))
    app.prepare(ctx_id=getattr(settings, "INSIGHTFACE_CTX_ID", -1))

    def read_image(field_file):
        with field_file.open("rb") as image_file:
            data = np.frombuffer(image_file.read(), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    id_image = read_image(kyc.id_front_image)
    live_image = read_image(kyc.live_face_image)
    id_faces = app.get(id_image)
    live_faces = app.get(live_image)

    if not id_faces or not live_faces:
        return {
            "confidence": Decimal("0.00"),
            "raw": {
                "id_faces": len(id_faces),
                "live_faces": len(live_faces),
            },
        }

    id_embedding = id_faces[0].normed_embedding
    live_embedding = live_faces[0].normed_embedding
    similarity = float(np.dot(id_embedding, live_embedding))
    confidence = max(0.0, min(100.0, (similarity + 1) * 50))
    return {
        "confidence": Decimal(str(round(confidence, 2))),
        "raw": {"cosine_similarity": similarity},
    }


def process_kyc(kyc):
    try:
        ocr = run_mindee_ocr(kyc)
        face = run_face_match(kyc)

        kyc.extracted_full_name = ocr.get("full_name", "")
        kyc.extracted_student_id = ocr.get("student_id", "")
        kyc.extracted_date_of_birth = ocr.get("date_of_birth", "")
        kyc.extracted_issue_date = ocr.get("issue_date", "")
        kyc.extracted_expiration_date = ocr.get("expiration_date", "")
        kyc.extracted_university_name = ocr.get("university_name", "")
        kyc.extracted_department = ocr.get("department", "")
        kyc.extracted_school = ocr.get("school", "")
        kyc.extracted_degree = ocr.get("degree", "")
        kyc.extracted_validity_period = ocr.get("validity_period", "")
        kyc.stamp_detected = bool(ocr.get("stamp_detected"))
        kyc.id_photo_detected = bool(ocr.get("id_photo_detected"))
        kyc.face_match_confidence = face.get("confidence")
        kyc.ocr_raw_response = ocr.get("raw", {})
        kyc.face_match_raw_response = face.get("raw", {})
        kyc.processed_at = timezone.now()

        minimum_confidence = Decimal(str(getattr(settings, "KYC_FACE_MATCH_THRESHOLD", 75)))
        if (
            kyc.stamp_detected
            and (kyc.face_match_confidence is None or kyc.face_match_confidence >= minimum_confidence)
        ):
            kyc.status = KYCVerification.Status.PENDING_REVIEW
        else:
            kyc.status = KYCVerification.Status.NEEDS_RETRY
    except Exception as exc:
        logger.exception("KYC processing failed for user %s", kyc.user_id)
        kyc.status = KYCVerification.Status.NEEDS_RETRY
        kyc.reviewer_notes = str(exc)
        kyc.processed_at = timezone.now()

    kyc.save()
    return kyc
