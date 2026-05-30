import logging
import re
from decimal import Decimal

import requests
from django.conf import settings
from django.utils import timezone

from .models import KYCVerification

logger = logging.getLogger(__name__)

_FACE_APP = None
_OCR_READER = None


def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _match_pattern(text, *patterns):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))
    return ""


def _parse_student_id_text(text):
    normalized = _clean_text(text)
    return {
        "full_name": _match_pattern(
            normalized,
            r"(?:name|student name)\s*[:\-]?\s*([A-Z][A-Z\s.'-]{3,80})(?=\s+(?:reg|registration|department|school|faculty|degree|program|course)|$)",
        ),
        "student_id": _match_pattern(
            normalized,
            r"(?:reg(?:istration)?\s*(?:no|number)?|admission\s*(?:no|number)?|student\s*(?:id|number))\s*[:\-]?\s*([A-Z0-9\/\-]{5,40})",
            r"\b([A-Z]{2,5}\d{2,4}[-\/]\d{2,6}[-\/]\d{2,4})\b",
        ),
        "department": _match_pattern(
            normalized,
            r"(?:department|dept)\s*[:\-]?\s*([A-Z][A-Z\s&.'-]{2,80})(?=\s+(?:school|faculty|degree|program|course|reg)|$)",
        ),
        "school": _match_pattern(
            normalized,
            r"(?:school|faculty)\s*[:\-]?\s*([A-Z][A-Z\s&.'-]{2,80})(?=\s+(?:department|degree|program|course|reg)|$)",
        ),
        "degree": _match_pattern(
            normalized,
            r"(?:degree|program|programme|course)\s*[:\-]?\s*([A-Z][A-Z\s&.'-]{2,100})(?=\s+(?:department|school|faculty|reg)|$)",
        ),
        "university_name": "Jomo Kenyatta University of Agriculture and Technology"
        if re.search(r"\b(jkuat|jomo kenyatta university)\b", normalized, re.IGNORECASE)
        else "",
        "raw_text": normalized,
    }


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


def _read_image_bytes(field_file):
    with field_file.open("rb") as image_file:
        return image_file.read()


def _decode_image(field_file):
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise ValueError("Image processing requires opencv-python and numpy.") from exc

    data = np.frombuffer(_read_image_bytes(field_file), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Uploaded image could not be decoded.")
    return image


def _get_easyocr_reader():
    global _OCR_READER
    if _OCR_READER is None:
        try:
            import easyocr
        except ImportError as exc:
            raise ValueError("Local OCR requires easyocr. Configure Mindee or install easyocr.") from exc
        _OCR_READER = easyocr.Reader(["en"], gpu=False)
    return _OCR_READER


def run_local_ocr(kyc):
    reader = _get_easyocr_reader()
    front_image = _decode_image(kyc.id_front_image)
    back_image = _decode_image(kyc.id_back_image)
    front_result = reader.readtext(front_image)
    back_result = reader.readtext(back_image)
    front_text = " ".join(text for _, text, _ in front_result)
    back_text = " ".join(text for _, text, _ in back_result)
    combined_text = f"{front_text} {back_text}"
    parsed = _parse_student_id_text(combined_text)

    return {
        "full_name": parsed["full_name"],
        "student_id": parsed["student_id"],
        "date_of_birth": _match_pattern(combined_text, r"(?:date of birth|dob)\s*[:\-]?\s*([0-9\/\-.]{6,12})"),
        "issue_date": _match_pattern(combined_text, r"(?:issue date|issued)\s*[:\-]?\s*([0-9\/\-.]{6,12})"),
        "expiration_date": _match_pattern(combined_text, r"(?:exp(?:iry|iration)? date|expires)\s*[:\-]?\s*([0-9\/\-.]{6,12})"),
        "university_name": parsed["university_name"],
        "department": parsed["department"],
        "school": parsed["school"],
        "degree": parsed["degree"],
        "validity_period": _match_pattern(combined_text, r"(?:validity|valid)\s*[:\-]?\s*([A-Z0-9\s\/\-.]{6,40})"),
        "stamp_detected": bool(re.search(r"\b(jkuat|jomo kenyatta university|registrar|official stamp)\b", combined_text, re.IGNORECASE)),
        "id_photo_detected": True,
        "raw": {
            "provider": "easyocr",
            "front_text": front_text,
            "back_text": back_text,
            "parsed": parsed,
        },
    }


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

    provider = str(getattr(settings, "KYC_OCR_PROVIDER", "mindee")).lower()
    api_key = getattr(settings, "MINDEE_API_KEY", "")
    endpoint = getattr(settings, "MINDEE_ENDPOINT_URL", "")
    if provider in {"local", "easyocr"}:
        return run_local_ocr(kyc)
    if not api_key or not endpoint:
        return run_local_ocr(kyc)

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
    parsed_text = _parse_student_id_text(str(front_raw) + " " + str(back_raw))

    return {
        "full_name": _first_present(front_prediction, "student_name", "full_name", "name") or parsed_text["full_name"],
        "student_id": _first_present(front_prediction, "student_id", "registration_number", "reg_number") or parsed_text["student_id"],
        "date_of_birth": _first_present(front_prediction, "date_of_birth", "dob"),
        "issue_date": _first_present(front_prediction, "issue_date", "issued_date"),
        "expiration_date": _first_present(front_prediction, "expiration_date", "expiry_date", "expiry"),
        "university_name": _first_present(front_prediction, "university_name", "institution_name") or parsed_text["university_name"],
        "department": _first_present(front_prediction, "department") or parsed_text["department"],
        "school": _first_present(front_prediction, "school", "faculty", "university_name") or parsed_text["school"],
        "degree": _first_present(front_prediction, "degree", "program", "course") or parsed_text["degree"],
        "validity_period": _first_present(front_prediction, "validity_period"),
        "stamp_detected": "jkuat" in back_text or "jomo kenyatta university" in back_text,
        "id_photo_detected": _has_object_detection(front_prediction, "student_photo", "photo", "passport_photo"),
        "raw": {"provider": "mindee", "front": front_raw, "back": back_raw, "parsed_text": parsed_text},
    }


def _get_face_app():
    global _FACE_APP
    if _FACE_APP is None:
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise ValueError("Face matching requires insightface.") from exc

        _FACE_APP = FaceAnalysis(name=getattr(settings, "INSIGHTFACE_MODEL_NAME", "buffalo_l"))
        _FACE_APP.prepare(ctx_id=getattr(settings, "INSIGHTFACE_CTX_ID", -1))
    return _FACE_APP


def _largest_face(faces):
    return max(faces, key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]))


def run_face_match(kyc):
    if not kyc.live_face_image:
        return {"confidence": None, "match": None, "confidence_label": "", "raw": {"skipped": "No live face image supplied."}}

    if getattr(settings, "KYC_MOCK", True):
        return {"confidence": Decimal("88.00"), "match": True, "confidence_label": "High", "raw": {"mode": "mock"}}

    import numpy as np

    app = _get_face_app()
    id_image = _decode_image(kyc.id_front_image)
    live_image = _decode_image(kyc.live_face_image)
    id_faces = app.get(id_image)
    live_faces = app.get(live_image)

    minimum_confidence = Decimal(str(getattr(settings, "KYC_FACE_MATCH_THRESHOLD", 75)))
    if not id_faces or not live_faces:
        return {
            "confidence": Decimal("0.00"),
            "match": False,
            "confidence_label": "Low",
            "raw": {
                "id_faces": len(id_faces),
                "live_faces": len(live_faces),
            },
        }

    id_embedding = _largest_face(id_faces).normed_embedding
    live_embedding = _largest_face(live_faces).normed_embedding
    similarity = float(np.dot(id_embedding, live_embedding))
    confidence = max(0.0, min(100.0, (similarity + 1) * 50))
    confidence_decimal = Decimal(str(round(confidence, 2)))
    confidence_label = "High" if confidence_decimal >= 80 else "Medium" if confidence_decimal >= 60 else "Low"
    return {
        "confidence": confidence_decimal,
        "match": confidence_decimal >= minimum_confidence,
        "confidence_label": confidence_label,
        "raw": {"cosine_similarity": similarity, "id_faces": len(id_faces), "live_faces": len(live_faces)},
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
        kyc.face_match_raw_response = {
            **face.get("raw", {}),
            "match": face.get("match"),
            "confidence_label": face.get("confidence_label", ""),
        }
        kyc.processed_at = timezone.now()

        minimum_confidence = Decimal(str(getattr(settings, "KYC_FACE_MATCH_THRESHOLD", 75)))
        has_identity_fields = bool(kyc.extracted_full_name or kyc.extracted_student_id)
        if kyc.face_match_confidence is not None and kyc.face_match_confidence < minimum_confidence:
            kyc.status = KYCVerification.Status.FACE_MISMATCH
        elif kyc.stamp_detected and has_identity_fields:
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
