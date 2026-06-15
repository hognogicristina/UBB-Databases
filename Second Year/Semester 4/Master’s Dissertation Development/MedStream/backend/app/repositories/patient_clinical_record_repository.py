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


from app.service.patient.discharge_service import PatientDischargeService
from app.service.patient.treatment_evaluator import PatientTreatmentEvaluator


class PatientClinicalRecordRepository:
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

    def __init__(self, treatment_evaluator: PatientTreatmentEvaluator | None = None, discharge_service: PatientDischargeService | None = None):
        self.treatment_evaluator = treatment_evaluator or PatientTreatmentEvaluator()
        self.discharge_service = discharge_service or PatientDischargeService()

    def _latest_treatment_action_outcome(self, db, patient_id: int) -> dict | None:
        return self.treatment_evaluator.get_latest_treatment_action_outcome(db, patient_id)

    def can_discharge_patient_as_recovered(self, db, patient_id: int, final_treatment: dict[str, Any] | None, **kwargs):
        return self.discharge_service.can_discharge_patient_as_recovered(db, patient_id, final_treatment, **kwargs)

    @staticmethod
    def _clamp_text(value: str, max_length: int) -> str:
        return (value or "")[:max_length]
    def get_patient_conditions(self, patient_id: int):
        with SessionLocal() as db:
            get_patient_or_raise(db, patient_id)
            rows = db.execute(
                select(PatientCondition, PatientConditionAssignment)
                .join(PatientConditionAssignment, PatientConditionAssignment.condition_id == PatientCondition.id)
                .where(PatientConditionAssignment.patient_id == patient_id)
                .order_by(PatientCondition.name.asc(), PatientCondition.id.asc())
            ).all()
            doctor_ids = {
                assignment.doctor_id
                for _, assignment in rows
                if assignment.doctor_id is not None
            }
            doctor_names = {}
            if doctor_ids:
                doctors = db.execute(
                    select(Doctor).where(Doctor.id.in_(doctor_ids))
                ).scalars().all()
                doctor_names = {
                    doctor.id: f"{doctor.last_name} {doctor.first_name}".strip()
                    for doctor in doctors
                }
            for _, assignment in rows:
                setattr(assignment, "modified_by", doctor_names.get(assignment.doctor_id))
            return rows
    def assign_patient_condition(self, patient_id: int, condition_id: int, doctor_id: int):
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            validate_patient_assignment(db, doctor_id, patient.id)
            validate_patient_editable(patient)

            condition = db.get(PatientCondition, condition_id)
            if condition is None:
                raise NotFoundError("CONDITION_NOT_FOUND")

            existing_assignment = db.execute(
                select(PatientConditionAssignment).where(
                    PatientConditionAssignment.patient_id == patient.id,
                    PatientConditionAssignment.condition_id == condition.id,
                )
            ).scalar_one_or_none()

            if existing_assignment is None:
                db.add(
                    PatientConditionAssignment(
                        patient_id=patient.id,
                        condition_id=condition.id,
                        doctor_id=doctor_id,
                    )
                )
                db.commit()

            rows = db.execute(
                select(PatientCondition, PatientConditionAssignment)
                .join(PatientConditionAssignment, PatientConditionAssignment.condition_id == PatientCondition.id)
                .where(PatientConditionAssignment.patient_id == patient.id)
                .order_by(PatientCondition.name.asc(), PatientCondition.id.asc())
            ).all()
            doctor_ids = {
                assignment.doctor_id
                for _, assignment in rows
                if assignment.doctor_id is not None
            }
            doctor_names = {}
            if doctor_ids:
                doctors = db.execute(
                    select(Doctor).where(Doctor.id.in_(doctor_ids))
                ).scalars().all()
                doctor_names = {
                    doctor.id: f"{doctor.last_name} {doctor.first_name}".strip()
                    for doctor in doctors
                }
            for _, assignment in rows:
                setattr(assignment, "modified_by", doctor_names.get(assignment.doctor_id))
            return rows
    def update_condition_assignment(self, assignment_id: int, doctor_id: int, status: str | None, notes: str | None):
        with SessionLocal() as db:
            assignment = db.get(PatientConditionAssignment, assignment_id)
            if assignment is None:
                raise NotFoundError("ASSIGNMENT_NOT_FOUND")

            validate_patient_assignment(db, doctor_id, assignment.patient_id)
            validate_patient_editable(get_patient_or_raise(db, assignment.patient_id))

            if status is not None:
                normalized_status = validate_condition_status(status)
                if normalized_status in {"resolved", "improving"}:
                    latest_treatment = self._latest_treatment_action_outcome(db, assignment.patient_id)
                    latest_outcome = latest_treatment["outcome"] if latest_treatment is not None else "Ineffective"
                    if normalized_status == "resolved" and latest_outcome != "Effective":
                        raise ValidationError("CONDITION_RESOLVE_REQUIRES_EFFECTIVE_FINAL_TREATMENT")
                    if normalized_status == "improving" and latest_outcome not in {"Effective", "Improving"}:
                        raise ValidationError("CONDITION_IMPROVING_REQUIRES_EFFECTIVE_FINAL_TREATMENT")
                    if normalized_status == "resolved":
                        can_resolve, _, _ = self.can_discharge_patient_as_recovered(
                            db,
                            assignment.patient_id,
                            latest_treatment,
                            discharge_timestamp=now_utc(),
                        )
                        if not can_resolve:
                            raise ValidationError("CONDITION_RESOLVE_REQUIRES_STABLE_LATEST_STATE")
                assignment.status = normalized_status
                assignment.doctor_id = doctor_id

            if notes is not None:
                assignment.notes = normalize_optional_text(notes)

            assignment.updated_at = now_utc()
            db.commit()
            db.refresh(assignment)
            return assignment
    def get_patient_allergies(self, patient_id: int, page: int, page_size: int) -> tuple[list[PatientAllergy], int]:
        with SessionLocal() as db:
            get_patient_or_raise(db, patient_id)

            total = db.execute(
                select(func.count()).select_from(PatientAllergy).where(PatientAllergy.patient_id == patient_id)
            ).scalar_one()

            allergies = db.execute(
                select(PatientAllergy)
                .where(PatientAllergy.patient_id == patient_id)
                .order_by(desc(PatientAllergy.updated_at), desc(PatientAllergy.id))
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars().all()

            return allergies, total
    def create_patient_allergy(self, patient_id: int, doctor_id: int, allergy_name: str, severity: str) -> PatientAllergy:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            validate_patient_assignment(db, doctor_id, patient.id)
            validate_patient_editable(patient)

            allergy = PatientAllergy(
                patient_id=patient.id,
                doctor_id=doctor_id,
                allergy_name=validate_required_text(allergy_name, "Allergy Name"),
                severity=validate_required_text(severity, "Severity"),
            )
            db.add(allergy)
            db.commit()
            db.refresh(allergy)
            return allergy
    def update_patient_allergy(self, allergy_id: int, doctor_id: int, severity: str | None) -> PatientAllergy:
        with SessionLocal() as db:
            allergy = db.get(PatientAllergy, allergy_id)
            if allergy is None:
                raise NotFoundError("ALLERGY_NOT_FOUND")

            validate_patient_assignment(db, doctor_id, allergy.patient_id)
            validate_patient_editable(get_patient_or_raise(db, allergy.patient_id))

            validate_update_value_present(severity, "NO_ALLERGY_UPDATES")

            allergy.severity = validate_required_text(severity, "Severity")
            allergy.updated_at = now_utc()
            db.commit()
            db.refresh(allergy)
            return allergy
    def get_patient_diagnosis(self, patient_id: int, page: int, page_size: int) -> tuple[list[PatientDiagnosis], int]:
        with SessionLocal() as db:
            get_patient_or_raise(db, patient_id)

            total = db.execute(
                select(func.count()).select_from(PatientDiagnosis).where(PatientDiagnosis.patient_id == patient_id)
            ).scalar_one()

            diagnosis_entries = db.execute(
                select(PatientDiagnosis)
                .where(PatientDiagnosis.patient_id == patient_id)
                .order_by(desc(PatientDiagnosis.updated_at), desc(PatientDiagnosis.id))
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars().all()
            doctor_ids = {
                diagnosis_entry.doctor_id
                for diagnosis_entry in diagnosis_entries
                if diagnosis_entry.doctor_id is not None
            }
            doctor_names = {}
            if doctor_ids:
                doctors = db.execute(
                    select(Doctor).where(Doctor.id.in_(doctor_ids))
                ).scalars().all()
                doctor_names = {
                    doctor.id: f"{doctor.last_name} {doctor.first_name}".strip()
                    for doctor in doctors
                }
            for diagnosis_entry in diagnosis_entries:
                setattr(diagnosis_entry, "modified_by", doctor_names.get(diagnosis_entry.doctor_id))

            return diagnosis_entries, total
    def create_patient_diagnosis(self, patient_id: int, doctor_id: int, diagnosis: str, notes: str | None) -> PatientDiagnosis:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            validate_patient_assignment(db, doctor_id, patient.id)
            validate_patient_editable(patient)

            diagnosis_entry = PatientDiagnosis(
                patient_id=patient.id,
                doctor_id=doctor_id,
                diagnosis=validate_required_text(diagnosis, "Diagnosis"),
                notes=normalize_optional_text(notes),
            )
            db.add(diagnosis_entry)
            db.commit()
            db.refresh(diagnosis_entry)
            doctor = db.get(Doctor, doctor_id)
            setattr(
                diagnosis_entry,
                "modified_by",
                f"{doctor.last_name} {doctor.first_name}".strip() if doctor is not None else None,
            )
            return diagnosis_entry
    def update_patient_diagnosis(
            self,
            diagnosis_id: int,
            doctor_id: int,
            status: str | None,
            note: str | None,
            notes: str | None,
    ) -> PatientDiagnosis:
        with SessionLocal() as db:
            diagnosis = db.get(PatientDiagnosis, diagnosis_id)
            if diagnosis is None:
                raise NotFoundError("DIAGNOSIS_NOT_FOUND")

            validate_patient_assignment(db, doctor_id, diagnosis.patient_id)
            validate_patient_editable(get_patient_or_raise(db, diagnosis.patient_id))

            updated = False

            if status is not None:
                normalized_status = validate_diagnosis_status(status)
                if normalized_status == "resolved":
                    latest_treatment = self._latest_treatment_action_outcome(db, diagnosis.patient_id)
                    latest_outcome = latest_treatment["outcome"] if latest_treatment is not None else "Ineffective"
                    if latest_outcome != "Effective":
                        raise ValidationError("DIAGNOSIS_RESOLVE_REQUIRES_EFFECTIVE_FINAL_TREATMENT")
                    can_resolve, _, _ = self.can_discharge_patient_as_recovered(
                        db,
                        diagnosis.patient_id,
                        latest_treatment,
                        discharge_timestamp=now_utc(),
                    )
                    if not can_resolve:
                        raise ValidationError("DIAGNOSIS_RESOLVE_REQUIRES_STABLE_LATEST_STATE")
                diagnosis.status = normalized_status
                diagnosis.doctor_id = doctor_id
                updated = True

            if note is not None:
                diagnosis.status_note = validate_required_text(note, "Note")
                updated = True

            if notes is not None:
                diagnosis.notes = normalize_optional_text(notes)
                diagnosis.doctor_id = doctor_id
                updated = True

            validate_non_empty_update(updated, "NO_DIAGNOSIS_UPDATES")

            diagnosis.updated_at = now_utc()
            db.commit()
            db.refresh(diagnosis)
            doctor = db.get(Doctor, diagnosis.doctor_id)
            setattr(
                diagnosis,
                "modified_by",
                f"{doctor.last_name} {doctor.first_name}".strip() if doctor is not None else None,
            )
            return diagnosis
    def administer_medication(
            self,
            patient_id: int,
            doctor_id: int,
            name: str,
            dosage: str,
            frequency: str,
            notes: str | None,
    ) -> PatientMedication:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            validate_patient_assignment(db, doctor_id, patient.id)
            validate_patient_editable(patient)

            medication = PatientMedication(
                patient_id=patient.id,
                doctor_id=doctor_id,
                name=self._clamp_text(
                    validate_medication_name(name, is_pregnant=patient.is_pregnant),
                    self.MEDICATION_NAME_MAX_LENGTH,
                ),
                dosage=self._clamp_text(validate_dosage(dosage), self.MEDICATION_DOSAGE_MAX_LENGTH),
                frequency=self._clamp_text(validate_frequency(frequency), self.MEDICATION_FREQUENCY_MAX_LENGTH),
                notes=normalize_optional_text(notes),
            )

            db.add(medication)
            db.commit()
            db.refresh(medication)
            return medication
    def get_patient_medications(self, patient_id: int) -> list[PatientMedication]:
        with SessionLocal() as db:
            get_patient_or_raise(db, patient_id)
            return db.execute(
                select(PatientMedication)
                .where(PatientMedication.patient_id == patient_id)
                .order_by(
                    desc(func.coalesce(PatientMedication.updated_at, PatientMedication.created_at)),
                    desc(PatientMedication.id),
                )
            ).scalars().all()
    def update_medication(self, medication_id: int, doctor_id: int, dosage: str | None, frequency: str | None,
                          note: str) -> PatientMedication:
        with SessionLocal() as db:
            medication = db.get(PatientMedication, medication_id)
            if medication is None:
                raise NotFoundError("MEDICATION_NOT_FOUND")

            validate_patient_assignment(db, doctor_id, medication.patient_id)
            validate_patient_editable(get_patient_or_raise(db, medication.patient_id))

            updated = False
            if dosage is not None:
                medication.dosage = self._clamp_text(
                    validate_dosage(dosage),
                    self.MEDICATION_DOSAGE_MAX_LENGTH,
                )
                updated = True

            if frequency is not None:
                medication.frequency = self._clamp_text(
                    validate_frequency(frequency),
                    self.MEDICATION_FREQUENCY_MAX_LENGTH,
                )
                updated = True

            validate_non_empty_update(updated, "NO_MEDICATION_UPDATES")

            medication.last_updated_note = validate_required_text(note, "Note")
            medication.updated_at = now_utc()

            db.commit()
            db.refresh(medication)
            return medication
    def get_condition_options(self) -> list[PatientCondition]:
        with SessionLocal() as db:
            return db.query(PatientCondition).all()
