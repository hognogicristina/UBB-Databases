from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.doctor.doctor import Doctor
from app.models.doctor.doctor_activity import DoctorActivity
from app.models.doctor.doctor_activity_patient import doctor_activity_patients
from app.models.patient.patient import Patient
from app.models.patient.patient_admission_history import PatientAdmissionHistory
from app.models.patient.patient_activity_doctor import patient_activity_doctors
from app.models.patient.patient_allergy import PatientAllergy
from app.models.patient.patient_condition import PatientCondition
from app.models.patient.patient_condition_assignment import PatientConditionAssignment
from app.models.patient.patient_diagnosis import PatientDiagnosis
from app.models.patient.patient_discharge_summary import PatientDischargeSummary
from app.models.patient.patient_medication import PatientMedication
from app.models.vital import Vital
from app.repositories.address_repository import AddressRepository
from app.validators.doctor_validators import validate_doctor_patient_specialization
from app.validators.medical_validators import (
    validate_condition_status,
    validate_diagnosis_status,
    validate_discharge_type,
    validate_dosage,
    validate_frequency,
    validate_medication_name,
)
from app.validators.patient_validators import (
    ConflictError,
    NotFoundError,
    get_patient_or_raise,
    normalize_optional_text,
    normalize_phone_value,
    validate_arrival_method,
    validate_cnp_immutable,
    validate_cnp_value,
    validate_department_value,
    validate_non_empty_update,
    validate_patient_discharged_for_readmit,
    validate_patient_assignment,
    validate_patient_editable,
    validate_patient_identity_uniqueness,
    validate_patient_name,
    validate_patient_not_already_discharged,
    validate_required_text,
    validate_gender_value,
    validate_update_value_present,
)
from app.alerts.alert_catalog import normalize_alert_type, vital_for_alert_type
from app.core.errors import ValidationError
from app.utils.datetime import now_utc, to_utc


from app.repositories.patient_assignment_repository import PatientAssignmentRepository
from app.service.patient.alert_state_service import PatientAlertStateService


class PatientCoreRepository(PatientAlertStateService):
    MEDICATION_NAME_MAX_LENGTH = 255
    MEDICATION_DOSAGE_MAX_LENGTH = 100
    MEDICATION_FREQUENCY_MAX_LENGTH = 100
    MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE = 10
    HEART_RATE_STABLE_MAX = 110
    OXYGEN_STABLE_MIN = 92
    TEMPERATURE_STABLE_MAX = 38

    ABNORMAL_ALERT_TYPES = {
        "heart_rate_high",
        "heart_rate_critical",
        "oxygen_low",
        "oxygen_critical",
        "temperature_high",
        "temperature_critical",
    }
    RECOVERY_ALERT_TYPES = {
        "heart_rate_normalized",
        "heart_rate_stable",
        "heart_rate_normal",
        "oxygen_normalized",
        "oxygen_stable",
        "oxygen_normal",
        "temperature_normalized",
        "temperature_stable",
        "temperature_normal",
    }
    VITAL_PRIORITY = ("oxygen_saturation", "heart_rate", "temperature")
    VITAL_LABELS = {
        "heart_rate": "heart rate",
        "oxygen_saturation": "oxygen saturation",
        "temperature": "temperature",
        "none": "none",
    }

    def __init__(self, address_repository: AddressRepository | None = None, assignment_repository: PatientAssignmentRepository | None = None):
        self.address_repository = address_repository or AddressRepository()
        self.assignment_repository = assignment_repository or PatientAssignmentRepository()

    def assign_doctor_to_patient_with_session(self, db, doctor_id: int, patient_id: int) -> None:
        self.assignment_repository.assign_doctor_to_patient_with_session(db, doctor_id, patient_id)

    def _load_patient_with_address(self, db, patient_id: int) -> Patient:
        patient = db.execute(
            select(Patient)
            .options(joinedload(Patient.address))
            .where(Patient.id == patient_id)
        ).scalar_one_or_none()
        if patient is None:
            raise NotFoundError("PATIENT_NOT_FOUND")
        return patient
    def _prepare_create_payload(self, payload: dict) -> tuple[dict, dict]:
        patient_data = {
            "first_name": validate_patient_name(payload.get("first_name"), "First Name"),
            "last_name": validate_patient_name(payload.get("last_name"), "Last Name"),
            "department": validate_department_value(payload.get("department")),
            "cnp": validate_cnp_value(payload.get("cnp")),
            "phone_number": normalize_phone_value(payload.get("phone_number")),
            "birth_date": payload.get("birth_date"),
            "gender": validate_gender_value(payload.get("gender")),
            "arrival_method": validate_arrival_method(payload.get("arrival_method")),
            "is_pregnant": bool(payload.get("is_pregnant", False)),
        }
        return patient_data, payload.get("address")
    def _prepare_update_payload(self, payload: dict) -> tuple[dict, dict | None]:
        updates: dict = {}

        if "first_name" in payload:
            updates["first_name"] = validate_patient_name(payload.get("first_name"), "First Name")
        if "last_name" in payload:
            updates["last_name"] = validate_patient_name(payload.get("last_name"), "Last Name")
        if "department" in payload:
            updates["department"] = validate_department_value(payload.get("department"))
        if "cnp" in payload:
            updates["cnp"] = validate_cnp_value(payload.get("cnp"))
        if "phone_number" in payload:
            updates["phone_number"] = normalize_phone_value(payload.get("phone_number"))
        if "gender" in payload:
            updates["gender"] = validate_gender_value(payload.get("gender"))
        if "birth_date" in payload:
            updates["birth_date"] = payload.get("birth_date")
        if "is_pregnant" in payload:
            updates["is_pregnant"] = payload.get("is_pregnant")

        address_updates = payload.get("address") if "address" in payload else None
        return updates, address_updates
    def list_patients(
        self,
        condition_id: int | None = None,
        department: str | None = None,
        alert_presence: str | None = None,
        status: str | None = None,
        treatment_outcome: str | None = None,
    ) -> list[Patient]:
        with SessionLocal() as db:
            patient_query = select(Patient).options(joinedload(Patient.address))

            if condition_id is not None:
                patient_query = patient_query.join(
                    PatientConditionAssignment,
                    PatientConditionAssignment.patient_id == Patient.id,
                ).where(PatientConditionAssignment.condition_id == condition_id)

            if department:
                patient_query = patient_query.where(Patient.department == validate_department_value(department))

            normalized_status = str(status or "all").strip().lower()
            if normalized_status == "admitted":
                patient_query = patient_query.where(Patient.is_discharged.is_(False))
            elif normalized_status == "discharged":
                patient_query = patient_query.where(Patient.is_discharged.is_(True))

            normalized_treatment_outcome = str(treatment_outcome or "all").strip().lower()
            if normalized_treatment_outcome not in {"all", ""} and normalized_status not in {"admitted", "discharged"}:
                patient_query = patient_query.where(Patient.is_discharged.is_(True))

            patients = db.execute(patient_query.order_by(desc(Patient.id))).scalars().all()

            if normalized_treatment_outcome not in {"all", ""} and patients:
                patient_ids = [patient.id for patient in patients]
                latest_summary_dates = (
                    select(
                        PatientDischargeSummary.patient_id,
                        func.max(PatientDischargeSummary.discharge_date).label("latest_discharge_date"),
                    )
                    .where(PatientDischargeSummary.patient_id.in_(patient_ids))
                    .group_by(PatientDischargeSummary.patient_id)
                    .subquery()
                )
                treatment_rows = db.execute(
                    select(PatientDischargeSummary.patient_id, PatientDischargeSummary.final_treatment_outcome)
                    .join(
                        latest_summary_dates,
                        (
                            (PatientDischargeSummary.patient_id == latest_summary_dates.c.patient_id)
                            & (PatientDischargeSummary.discharge_date == latest_summary_dates.c.latest_discharge_date)
                        ),
                    )
                ).all()
                matching_patient_ids = {
                    patient_id
                    for patient_id, final_treatment_outcome in treatment_rows
                    if str(final_treatment_outcome or "").strip().lower() == normalized_treatment_outcome
                }
                patients = [patient for patient in patients if patient.id in matching_patient_ids]

            normalized_alert_presence = str(alert_presence or "all").strip().lower()
            if normalized_alert_presence in {"all", ""} or not patients:
                return patients

            patient_ids = [patient.id for patient in patients]
            alerts = db.execute(
                select(Alert)
                .where(Alert.patient_id.in_(patient_ids))
                .order_by(Alert.created_at.asc(), Alert.id.asc())
            ).scalars().all()
            alerts_by_patient: dict[int, list[Alert]] = {}
            for alert in alerts:
                alerts_by_patient.setdefault(alert.patient_id, []).append(alert)

            def matches_alert_filter(patient: Patient) -> bool:
                current_level = self._current_alert_level(alerts_by_patient.get(patient.id, []))
                if normalized_alert_presence == "any":
                    return current_level != "none"
                if normalized_alert_presence == "none":
                    return current_level == "none"
                return current_level == normalized_alert_presence

            return [patient for patient in patients if matches_alert_filter(patient)]
    def search_patients_by_cnp(self, cnp: str, limit: int = 10) -> list[Patient]:
        normalized_cnp = (cnp or "").strip()
        if not normalized_cnp:
            return []

        with SessionLocal() as db:
            return db.execute(
                select(Patient)
                .options(joinedload(Patient.address))
                .where(Patient.cnp.like(f"%{normalized_cnp}%"))
                .order_by(Patient.cnp.asc(), Patient.id.asc())
                .limit(max(1, min(limit, 20)))
            ).scalars().all()
    def get_patient(self, patient_id: int) -> Patient:
        with SessionLocal() as db:
            return self._load_patient_with_address(db, patient_id)
    def create_patient(self, payload: dict, doctor_id: int | None = None) -> Patient:
        with SessionLocal() as db:
            patient_data, address_payload = self._prepare_create_payload(payload)
            validate_patient_identity_uniqueness(
                db,
                cnp=patient_data["cnp"],
                phone_number=patient_data["phone_number"],
            )

            address = self.address_repository.create_address_with_session(db, address_payload)

            patient = Patient(**patient_data, address_id=address.id)
            db.add(patient)

            try:
                db.flush()
                if doctor_id is not None:
                    self.assign_doctor_to_patient_with_session(db, doctor_id, patient.id)

                db.add(
                    PatientAdmissionHistory(
                        patient_id=patient.id,
                        doctor_id=doctor_id,
                        type="admission",
                        reason=None,
                        note=self._admission_note_from_arrival_method(patient.arrival_method),
                        created_at=datetime.now(timezone.utc),
                    )
                )
                db.commit()
                return self._load_patient_with_address(db, patient.id)
            except IntegrityError as error:
                db.rollback()
                raise ConflictError("PATIENT_IDENTITY_FIELDS_UNIQUE") from error
    def update_patient(self, patient_id: int, doctor_id: int, payload: dict) -> Patient:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            validate_patient_assignment(db, doctor_id, patient.id)
            validate_patient_editable(patient)

            updates, address_updates = self._prepare_update_payload(payload)

            if "cnp" in updates:
                validate_cnp_immutable(patient.cnp, updates["cnp"])
                updates.pop("cnp")

            if "phone_number" in updates:
                validate_patient_identity_uniqueness(
                    db,
                    phone_number=updates.get("phone_number"),
                    patient_id=patient.id,
                )

            for field, value in updates.items():
                setattr(patient, field, value)

            updated_address = self.address_repository.upsert_address_with_session(db, patient.address, address_updates)
            if updated_address is not None:
                patient.address_id = updated_address.id

            try:
                db.commit()
                return self._load_patient_with_address(db, patient.id)
            except IntegrityError as error:
                db.rollback()
                raise ConflictError("PATIENT_IDENTITY_FIELDS_UNIQUE") from error
    def update_patient_department(self, patient_id: int, doctor_id: int, department: str, reason: str) -> Patient:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            validate_patient_assignment(db, doctor_id, patient.id)
            validate_patient_editable(patient)

            patient.department = validate_department_value(department)
            validate_required_text(reason, "Reason")

            db.commit()
            return self._load_patient_with_address(db, patient.id)
