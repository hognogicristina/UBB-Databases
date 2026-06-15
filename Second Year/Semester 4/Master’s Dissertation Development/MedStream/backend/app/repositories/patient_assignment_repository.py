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
from app.service.patient.alert_state_service import PatientAlertStateService


class PatientAssignmentRepository(PatientAlertStateService):
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

    def _load_patient_with_address(self, db, patient_id: int) -> Patient:
        patient = db.execute(
            select(Patient)
            .options(joinedload(Patient.address))
            .where(Patient.id == patient_id)
        ).scalar_one_or_none()
        if patient is None:
            raise NotFoundError("PATIENT_NOT_FOUND")
        return patient

    def _latest_treatment_action_outcome(self, db, patient_id: int) -> dict | None:
        return self.treatment_evaluator.get_latest_treatment_action_outcome(db, patient_id)

    def can_discharge_patient_as_recovered(self, db, patient_id: int, final_treatment: dict[str, Any] | None, **kwargs):
        return self.discharge_service.can_discharge_patient_as_recovered(db, patient_id, final_treatment, **kwargs)

    @staticmethod
    def _admission_note_from_arrival_method(arrival_method: str) -> str:
        if arrival_method == "ambulance":
            return "Arrived by ambulance"
        return "Arrived by themselves"
    @staticmethod
    def _cancel_incoming_patient_activities(db, patient_id: int) -> None:
        activities = (
            db.query(DoctorActivity)
            .filter(
                DoctorActivity.patient_id == patient_id,
                DoctorActivity.status == "incoming",
            )
            .all()
        )
        for activity in activities:
            activity.status = "canceled"
    def assign_doctor_to_patient_with_session(self, db, doctor_id: int, patient_id: int) -> None:
        exists = db.execute(
            doctor_activity_patients.select().where(
                (doctor_activity_patients.c.doctor_id == doctor_id)
                & (doctor_activity_patients.c.patient_id == patient_id)
            )
        ).first()

        if not exists:
            db.execute(
                doctor_activity_patients.insert().values(
                    doctor_id=doctor_id,
                    patient_id=patient_id,
                )
            )
    def get_patient_doctors(self, patient_id: int) -> list[Doctor]:
        with SessionLocal() as db:
            patient = db.execute(
                select(Patient).options(selectinload(Patient.doctors)).where(Patient.id == patient_id)
            ).scalar_one_or_none()
            if patient is None:
                raise NotFoundError("PATIENT_NOT_FOUND")
            return sorted(patient.doctors, key=lambda doctor: doctor.id, reverse=True)
    def discharge_patient(self, patient_id: int, doctor_id: int, discharge_type: str, reason: str) -> Patient:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            validate_patient_assignment(db, doctor_id, patient.id)

            validate_patient_not_already_discharged(patient.is_discharged)

            normalized_type = validate_discharge_type(discharge_type)
            normalized_reason = validate_required_text(reason, "Reason")
            latest_treatment = self._latest_treatment_action_outcome(db, patient.id)
            latest_outcome = latest_treatment["outcome"] if latest_treatment is not None else "Ineffective"
            discharge_timestamp = datetime.now(timezone.utc)
            if latest_outcome == "Improving":
                raise ValidationError("DISCHARGE_NOT_ALLOWED_FOR_IMPROVING_OUTCOME")
            if normalized_type == "Recovered":
                if latest_outcome != "Effective":
                    raise ValidationError("DISCHARGE_RECOVERED_REQUIRES_EFFECTIVE_FINAL_TREATMENT")
                can_discharge, reason_code, debug_payload = self.can_discharge_patient_as_recovered(
                    db,
                    patient.id,
                    latest_treatment,
                    discharge_timestamp=discharge_timestamp,
                )
                print(
                    f"[RECOVERED_DISCHARGE_GUARD] patient_id={patient.id} patient_name={patient.last_name} {patient.first_name} "
                    f"allowed={can_discharge} reason={reason_code} payload={debug_payload}"
                )
                if not can_discharge:
                    raise ValidationError("DISCHARGE_RECOVERED_REQUIRES_STABLE_LATEST_STATE")
            elif normalized_type == "Transferred" and latest_outcome != "Ineffective":
                raise ValidationError("TRANSFER_DISCHARGE_REQUIRES_INEFFECTIVE_FINAL_TREATMENT")
            self._cancel_incoming_patient_activities(db, patient.id)

            patient.is_discharged = True
            patient.discharge_reason = normalized_reason
            patient.discharge_date = discharge_timestamp

            db.add(
                PatientAdmissionHistory(
                    patient_id=patient.id,
                    doctor_id=doctor_id,
                    type=normalized_type,
                    reason=normalized_reason,
                    created_at=patient.discharge_date,
                )
            )

            db.commit()
            return self._load_patient_with_address(db, patient.id)
    def readmit_patient(self, patient_id: int, doctor_id: int, doctor_specialization: str, arrival_method: str) -> Patient:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)

            validate_patient_discharged_for_readmit(patient.is_discharged)
            normalized_arrival_method = validate_arrival_method(arrival_method)

            if patient.department != doctor_specialization:
                patient.department = doctor_specialization

            patient.arrival_method = normalized_arrival_method
            patient.is_discharged = False
            patient.discharge_reason = None
            patient.discharge_date = None

            self.assign_doctor_to_patient_with_session(db, doctor_id, patient.id)

            db.add(
                PatientAdmissionHistory(
                    patient_id=patient.id,
                    doctor_id=doctor_id,
                    type="admission",
                    reason=None,
                    note=self._admission_note_from_arrival_method(normalized_arrival_method),
                    created_at=datetime.now(timezone.utc),
                )
            )

            db.commit()
            return self._load_patient_with_address(db, patient.id)
    def transfer_patient_assignment(
            self,
            patient_id: int,
            current_doctor_id: int,
            from_doctor_id: int,
            to_doctor_id: int,
    ) -> Patient:
        with SessionLocal() as db:
            patient = db.execute(
                select(Patient)
                .options(selectinload(Patient.doctors), joinedload(Patient.address))
                .where(Patient.id == patient_id)
            ).scalar_one_or_none()
            if patient is None:
                raise NotFoundError("PATIENT_NOT_FOUND")

            validate_patient_assignment(db, current_doctor_id, patient.id)
            validate_patient_editable(patient)

            if to_doctor_id <= 0:
                raise ValidationError("TRANSFER_TARGET_REQUIRED")
            if from_doctor_id == to_doctor_id:
                raise ValidationError("TRANSFER_TO_SELF_NOT_ALLOWED")

            from_doctor = db.get(Doctor, from_doctor_id)
            if from_doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")
            validate_patient_assignment(db, from_doctor.id, patient.id)

            available_doctors = db.execute(
                select(Doctor)
                .where(
                    Doctor.is_active.is_(True),
                    Doctor.specialization == patient.department,
                    Doctor.id != from_doctor_id,
                )
            ).scalars().all()

            replacement_doctor = next((doctor for doctor in available_doctors if doctor.id == to_doctor_id), None)
            if replacement_doctor is None:
                raise ValidationError("TRANSFER_TARGET_NOT_AVAILABLE")

            validate_doctor_patient_specialization(replacement_doctor, patient)

            incoming_activities = (
                db.query(DoctorActivity)
                .filter(
                    DoctorActivity.patient_id == patient.id,
                    DoctorActivity.status == "incoming",
                )
                .all()
            )

            for activity in incoming_activities:
                activity.status = "canceled"

                migrated_activity = DoctorActivity(
                    doctor_id=replacement_doctor.id,
                    patient_id=patient.id,
                    type=activity.type,
                    title=activity.title,
                    description=activity.description,
                    status="incoming",
                    scheduled_at=activity.scheduled_at,
                )
                migrated_activity.patients = [patient]
                migrated_activity.doctors = [replacement_doctor]
                db.add(migrated_activity)

            if not any(doctor.id == replacement_doctor.id for doctor in patient.doctors):
                patient.doctors.append(replacement_doctor)

            source_doctor = next((doctor for doctor in patient.doctors if doctor.id == from_doctor_id), None)
            if source_doctor is not None:
                patient.doctors.remove(source_doctor)

            db.commit()
            return self._load_patient_with_address(db, patient.id)
    def get_patient_admission_history(self, patient_id: int, page: int, page_size: int) -> tuple[list[PatientAdmissionHistory], int]:
        with SessionLocal() as db:
            get_patient_or_raise(db, patient_id)

            total = db.execute(
                select(func.count()).select_from(PatientAdmissionHistory).where(PatientAdmissionHistory.patient_id == patient_id)
            ).scalar_one()

            entries = db.execute(
                select(PatientAdmissionHistory)
                .where(PatientAdmissionHistory.patient_id == patient_id)
                .order_by(desc(PatientAdmissionHistory.created_at), desc(PatientAdmissionHistory.id))
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).scalars().all()

            return entries, total
    def get_patient_activities(self, patient_id: int) -> list[DoctorActivity]:
        with SessionLocal() as db:
            get_patient_or_raise(db, patient_id)
            return db.execute(
                select(DoctorActivity)
                .join(patient_activity_doctors, patient_activity_doctors.c.activity_id == DoctorActivity.id)
                .where(patient_activity_doctors.c.patient_id == patient_id)
                .options(
                    selectinload(DoctorActivity.doctors),
                    selectinload(DoctorActivity.patients),
                )
                .order_by(desc(DoctorActivity.scheduled_at), desc(DoctorActivity.id))
            ).scalars().all()
