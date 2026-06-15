from __future__ import annotations

from app.core.errors import ValidationError
from app.service.clinical_records import DISCHARGE, DOSAGES, DRUGS, FREQUENCIES, STATUS
from app.validators.patient_validators import validate_required_text

ALLOWED_DIAGNOSIS_STATUSES = {"active", "resolved", "chronic", "inactive"}


def validate_condition_status(value: str | None) -> str:
    normalized = validate_required_text(value, "Condition status")
    if normalized not in STATUS:
        raise ValidationError("INVALID_CONDITION_STATUS")
    return normalized


def validate_diagnosis_status(value: str | None) -> str:
    normalized = validate_required_text(value, "Diagnosis status")
    if normalized not in ALLOWED_DIAGNOSIS_STATUSES:
        raise ValidationError("INVALID_DIAGNOSIS_STATUS")
    return normalized


def validate_discharge_type(value: str | None) -> str:
    normalized = validate_required_text(value, "Type")
    if normalized not in DISCHARGE:
        raise ValidationError("INVALID_DISCHARGE_TYPE")
    return normalized


def validate_medication_name(name: str, *, is_pregnant: bool) -> str:
    normalized_name = validate_required_text(name, "Medication")
    matching_drugs = [drug for drug in DRUGS if drug["medication"] == normalized_name]
    if not matching_drugs:
        raise ValidationError("INVALID_MEDICATION")

    allowed_categories = {"A", "B"} if is_pregnant else {"A", "B", "C", "D", "N"}
    has_allowed_option = any(
        ((drug.get("pregnancy_category") or "N").strip() or "N") in allowed_categories
        for drug in matching_drugs
    )

    if not has_allowed_option:
        if is_pregnant:
            raise ValidationError("MEDICATION_NOT_ALLOWED_PREGNANT")
        raise ValidationError("MEDICATION_NOT_ALLOWED")

    return normalized_name


def validate_dosage(value: str) -> str:
    normalized = validate_required_text(value, "Dosage")
    if normalized not in DOSAGES:
        raise ValidationError("INVALID_DOSAGE")
    return normalized


def validate_frequency(value: str) -> str:
    normalized = validate_required_text(value, "Frequency")
    if normalized not in FREQUENCIES:
        raise ValidationError("INVALID_FREQUENCY")
    return normalized
