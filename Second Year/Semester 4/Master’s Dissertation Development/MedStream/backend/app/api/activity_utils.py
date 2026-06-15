from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.doctor.doctor import Doctor
from app.models.doctor.doctor_activity import DoctorActivity
from app.models.patient.patient import Patient
from app.schemas.doctor_activity import DoctorActivityRead
from app.service.clinical_records import ACTIVITY_TYPES


def serialize_activity(activity: DoctorActivity) -> dict:
    patients = list(activity.patients or [])
    doctors = list(activity.doctors or [])

    patient_ids = [patient.id for patient in patients]
    if not patient_ids and getattr(activity, "patient_id", None) is not None:
        patient_ids = [activity.patient_id]

    doctor_ids = [doctor.id for doctor in doctors]
    if not doctor_ids and getattr(activity, "doctor_id", None) is not None:
        doctor_ids = [activity.doctor_id]

    payload = {
        **activity.__dict__,
        "patient_ids": patient_ids,
        "doctor_ids": doctor_ids,
        "patients": [
            {
                "id": patient.id,
                "first_name": patient.first_name,
                "last_name": patient.last_name,
            }
            for patient in patients
        ],
        "doctors": [
            {
                "id": doctor.id,
                "first_name": doctor.first_name,
                "last_name": doctor.last_name,
            }
            for doctor in doctors
        ],
    }
    return DoctorActivityRead.model_validate(payload).model_dump(mode="json")


def serialize_activities(activities: Iterable[DoctorActivity]) -> list[dict]:
    return [serialize_activity(activity) for activity in activities]


def load_activity_or_404(db, activity_id: int) -> DoctorActivity:
    activity = db.execute(
        select(DoctorActivity)
        .options(selectinload(DoctorActivity.patients), selectinload(DoctorActivity.doctors))
        .where(DoctorActivity.id == activity_id)
    ).scalar_one_or_none()

    if activity is None:
        raise NotFoundError("ACTIVITY_NOT_FOUND")

    return activity


def ensure_supported_activity_type(activity_type: str):
    if activity_type not in ACTIVITY_TYPES:
        raise ValidationError("INVALID_ACTIVITY_TYPE")


def _unique_ids(raw_ids: list[int], label: str) -> list[int]:
    unique_ids = list(dict.fromkeys(raw_ids))
    if len(unique_ids) != len(raw_ids):
        raise ValidationError("DUPLICATE_ASSIGNMENT", context={"label": label})
    return unique_ids


def load_patients_for_activity(db, patient_ids: list[int]) -> list[Patient]:
    normalized_ids = _unique_ids(patient_ids, "patient")
    patients = db.execute(
        select(Patient)
        .options(selectinload(Patient.doctors))
        .where(Patient.id.in_(normalized_ids))
    ).scalars().all()

    if len(patients) != len(normalized_ids):
        raise NotFoundError("ACTIVITY_PATIENTS_NOT_FOUND")

    by_id = {patient.id: patient for patient in patients}
    return [by_id[patient_id] for patient_id in normalized_ids]


def load_doctors_for_activity(db, doctor_ids: list[int]) -> list[Doctor]:
    normalized_ids = _unique_ids(doctor_ids, "doctor")
    doctors = db.execute(
        select(Doctor)
        .where(Doctor.id.in_(normalized_ids))
    ).scalars().all()

    if len(doctors) != len(normalized_ids):
        raise NotFoundError("ACTIVITY_DOCTORS_NOT_FOUND")

    by_id = {doctor.id: doctor for doctor in doctors}
    return [by_id[doctor_id] for doctor_id in normalized_ids]


def ensure_activity_departments_match(patients: list[Patient], doctors: list[Doctor]):
    patient_departments = {patient.department for patient in patients}

    if len(patient_departments) > 1:
        raise ValidationError("ACTIVITY_PATIENT_DEPARTMENTS_MISMATCH")

    if not patient_departments:
        return

    department = next(iter(patient_departments))
    invalid_doctors = [doctor for doctor in doctors if doctor.specialization != department]

    if invalid_doctors:
        raise ValidationError("ACTIVITY_DOCTOR_DEPARTMENTS_MISMATCH")


def ensure_activity_patients_match_doctor_department(patients: list[Patient], doctor: Doctor):
    invalid_patients = [patient for patient in patients if patient.department != doctor.specialization]

    if invalid_patients:
        raise ValidationError("ACTIVITY_PATIENT_DOCTOR_DEPARTMENT_MISMATCH")


def ensure_activity_patients_are_editable(patients: list[Patient]):
    if any(patient.is_discharged for patient in patients):
        raise ValidationError("ACTIVITY_DISCHARGED_PATIENT_MODIFY_FORBIDDEN")


def ensure_activity_modifier(activity: DoctorActivity, doctor_id: int):
    assigned_doctor_ids = {doctor.id for doctor in activity.doctors}
    if not assigned_doctor_ids and getattr(activity, "doctor_id", None) is not None:
        assigned_doctor_ids.add(activity.doctor_id)

    if doctor_id not in assigned_doctor_ids:
        raise PermissionDeniedError("ACTIVITY_MODIFIER_FORBIDDEN")


def attach_activity_relationships(activity: DoctorActivity, patients: list[Patient], doctors: list[Doctor]):
    activity.patients = patients
    activity.doctors = doctors
    activity.patient_id = patients[0].id if patients else None
    activity.doctor_id = doctors[0].id if doctors else activity.doctor_id

    for patient in patients:
        for doctor in doctors:
            if doctor not in patient.doctors:
                patient.doctors.append(doctor)
