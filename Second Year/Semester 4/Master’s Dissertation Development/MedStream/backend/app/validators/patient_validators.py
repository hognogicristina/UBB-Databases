from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models.patient.patient import Patient
from app.service.clinical_records import DEPARTMENTS
from app.validators.common_validators import (
    normalize_optional_text,
    require_non_empty,
    strip_string,
    validate_text_length,
)

ROMANIA_COUNTRY = "Romania"
CNP_CONTROL_WEIGHTS = "279146358279"
ALLOWED_ARRIVAL_METHODS = {"ambulance", "self"}


def validate_required_text(value: str | None, field_label: str) -> str:
    return require_non_empty(value, field_label)


def validate_patient_name(value: str | None, field_label: str) -> str:
    name = require_non_empty(value, field_label)
    return validate_text_length(name, field_label, 100)


def validate_gender_value(value: str | None) -> str:
    gender = require_non_empty(value, "Gender")
    return validate_text_length(gender, "Gender", 20)


def validate_department_value(value: str | None) -> str:
    department = require_non_empty(value, "Department")
    if department not in DEPARTMENTS:
        raise ValidationError("INVALID_DEPARTMENT")
    return department


def validate_cnp_value(value: str | None) -> str:
    cnp = require_non_empty(value, "CNP")

    if not re.fullmatch(r"\d{13}", cnp):
        raise ValidationError("INVALID_CNP_DIGITS")

    checksum_total = sum(
        int(digit) * int(weight) for digit, weight in zip(cnp[:12], CNP_CONTROL_WEIGHTS, strict=True)
    )
    checksum = checksum_total % 11
    checksum = 1 if checksum == 10 else checksum

    if checksum != int(cnp[-1]):
        raise ValidationError("INVALID_CNP_CHECKSUM")

    return cnp


def normalize_phone_value(value: str | None):
    raw_value = strip_string(value)

    if not raw_value:
        return None

    has_plus_prefix = raw_value.startswith("+")
    digits = "".join(char for char in raw_value if char.isdigit())

    if not digits:
        return None

    if digits.startswith("0040") and len(digits) == 13 and digits[4] == "7":
        return f"+{digits[2:]}"

    if digits.startswith("40") and len(digits) == 11 and digits[2] == "7":
        return f"+{digits}"

    if digits.startswith("07") and len(digits) == 10:
        return f"+4{digits}"

    if 8 <= len(digits) <= 15 and (has_plus_prefix or not digits.startswith("0")):
        return f"+{digits}"

    raise ValidationError("INVALID_PHONE_FORMAT")


def phone_uniqueness_values(value: str | None) -> set[str]:
    normalized = normalize_phone_value(value)
    if not normalized:
        return set()

    values = {normalized}
    digits = "".join(char for char in normalized if char.isdigit())

    if digits.startswith("40") and len(digits) == 11 and digits[2] == "7":
        values.add(f"0{digits[2:]}")

    return values


def validate_arrival_method(value: str | None) -> str:
    normalized = validate_required_text(value or "self", "Arrival method").lower()
    if normalized not in ALLOWED_ARRIVAL_METHODS:
        raise ValidationError("INVALID_ARRIVAL_METHOD")
    return normalized


def get_patient_or_raise(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError("PATIENT_NOT_FOUND")
    return patient


def validate_patient_assignment(db: Session, doctor_id: int, patient_id: int) -> None:
    is_assigned = db.execute(
        select(Patient.id)
        .join(Patient.doctors.property.secondary, Patient.doctors.property.secondary.c.patient_id == Patient.id)
        .where(Patient.doctors.property.secondary.c.doctor_id == doctor_id, Patient.id == patient_id)
    ).scalar_one_or_none()

    if is_assigned is None:
        raise PermissionDeniedError("DOCTOR_MUST_BE_ASSIGNED_TO_PATIENT")


def validate_patient_editable(patient: Patient) -> None:
    if patient.is_discharged:
        raise ValidationError("DISCHARGED_PATIENT_NOT_EDITABLE")


def validate_patient_identity_uniqueness(
        db: Session,
        *,
        cnp: str | None = None,
        phone_number: str | None = None,
        patient_id: int | None = None,
) -> None:
    if cnp:
        cnp_query = select(Patient).where(Patient.cnp == cnp)
        if patient_id is not None:
            cnp_query = cnp_query.where(Patient.id != patient_id)
        if db.execute(cnp_query).scalar_one_or_none():
            raise ConflictError("CNP_ALREADY_REGISTERED")

    if phone_number:
        phone_values = phone_uniqueness_values(phone_number)
        phone_query = select(Patient).where(Patient.phone_number.in_(phone_values))
        if patient_id is not None:
            phone_query = phone_query.where(Patient.id != patient_id)
        if db.execute(phone_query).scalar_one_or_none():
            raise ConflictError("PHONE_ALREADY_REGISTERED")


def validate_cnp_immutable(existing_cnp: str, proposed_cnp: str) -> None:
    if proposed_cnp != existing_cnp:
        raise ValidationError("CNP_IMMUTABLE")


def validate_patient_not_already_discharged(is_discharged: bool) -> None:
    if is_discharged:
        raise ValidationError("PATIENT_ALREADY_DISCHARGED")


def validate_patient_discharged_for_readmit(is_discharged: bool) -> None:
    if not is_discharged:
        raise ValidationError("PATIENT_NOT_DISCHARGED")


def validate_update_value_present(value, code: str) -> None:
    if value is None:
        raise ValidationError(code)


def validate_non_empty_update(updated: bool, code: str) -> None:
    if not updated:
        raise ValidationError(code)
