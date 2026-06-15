from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import func, select

from app.core.errors import ValidationError
from app.db.session import SessionLocal
from app.models.address import Address
from app.models.alert import Alert
from app.models.doctor.doctor import Doctor
from app.models.doctor.doctor_activity import DoctorActivity
from app.models.doctor.doctor_activity_patient import doctor_activity_patients
from app.models.encounter import Encounter
from app.models.patient.patient import Patient
from app.models.patient.patient_admission_history import PatientAdmissionHistory
from app.models.patient.patient_allergy import PatientAllergy
from app.models.patient.patient_condition import PatientCondition
from app.models.patient.patient_condition_assignment import PatientConditionAssignment
from app.models.patient.patient_diagnosis import PatientDiagnosis
from app.models.patient.patient_medication import PatientMedication
from app.models.vital import Vital
from app.service.assign_patients import assign_doctor_to_patient
from app.utils.datetime import now_utc
from app.validators.doctor_validators import validate_activity_creation


class SimulatorRepository:
    MEDICATION_NAME_MAX_LENGTH = 255
    MEDICATION_DOSAGE_MAX_LENGTH = 100
    MEDICATION_FREQUENCY_MAX_LENGTH = 100

    DIAGNOSIS_ALLOWED_STATUSES = {"active", "resolved", "chronic", "inactive"}
    CONDITION_ALLOWED_STATUSES = {"active", "improving", "stable", "worsening", "critical", "resolved", "chronic"}

    DIAGNOSIS_STATUS_FALLBACKS = {
        "improving": "active",
        "stable": "active",
        "worsening": "active",
        "critical": "active",
        "monitoring": "active",
    }
    CONDITION_STATUS_FALLBACKS = {
        "inactive": "stable",
        "monitoring": "stable",
    }

    @staticmethod
    def _normalize_status(value: str | None) -> str:
        return str(value or "").strip().lower()

    def _sanitize_diagnosis_status(self, value: str | None) -> str:
        normalized = self._normalize_status(value)
        if normalized in self.DIAGNOSIS_ALLOWED_STATUSES:
            return normalized
        return self.DIAGNOSIS_STATUS_FALLBACKS.get(normalized, "active")

    def _sanitize_condition_status(self, value: str | None) -> str:
        normalized = self._normalize_status(value)
        if normalized in self.CONDITION_ALLOWED_STATUSES:
            return normalized
        return self.CONDITION_STATUS_FALLBACKS.get(normalized, "active")

    @staticmethod
    def _clamp_text(value: str, max_length: int) -> str:
        return (value or "")[:max_length]

    @contextmanager
    def session_scope(self):
        db = SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_doctor_count(self, db) -> int:
        return db.query(Doctor).count()

    def get_doctor_by_email(self, db, email: str) -> Doctor | None:
        return db.execute(
            select(Doctor).where(func.lower(Doctor.email) == (email or "").strip().lower())
        ).scalar_one_or_none()

    def get_doctor_by_email_or_license(self, db, *, email: str, license_number: str) -> Doctor | None:
        normalized_email = (email or "").strip().lower()
        normalized_license = (license_number or "").strip()
        return db.execute(
            select(Doctor).where(
                (func.lower(Doctor.email) == normalized_email)
                | (Doctor.license_number == normalized_license)
            )
        ).scalars().first()

    def create_doctor(self, db, payload: dict) -> Doctor:
        doctor = Doctor(**payload)
        db.add(doctor)
        return doctor

    def get_random_doctor(self, db) -> Doctor | None:
        return (
            db.query(Doctor)
            .filter(Doctor.is_active.is_(True), Doctor.deleted_at.is_(None))
            .order_by(func.random())
            .first()
        )

    def get_random_doctor_for_department(self, db, department: str) -> Doctor | None:
        return (
            db.query(Doctor)
            .filter(
                Doctor.specialization == department,
                Doctor.is_active.is_(True),
                Doctor.deleted_at.is_(None),
            )
            .order_by(func.random())
            .first()
        )

    def get_doctor(self, db, doctor_id: int) -> Doctor | None:
        return db.get(Doctor, doctor_id)

    def is_phone_available(
            self,
            db,
            phone_number: str,
            *,
            exclude_doctor_id: int | None = None,
            exclude_patient_id: int | None = None,
    ) -> bool:
        normalized = (phone_number or "").strip()
        if not normalized:
            return False

        doctor_query = select(Doctor).where(func.lower(Doctor.phone_number) == normalized.lower())
        if exclude_doctor_id is not None:
            doctor_query = doctor_query.where(Doctor.id != exclude_doctor_id)
        existing_doctor = db.execute(doctor_query).scalar_one_or_none()
        if existing_doctor is not None:
            return False

        patient_query = select(Patient).where(func.lower(Patient.phone_number) == normalized.lower())
        if exclude_patient_id is not None:
            patient_query = patient_query.where(Patient.id != exclude_patient_id)
        existing_patient = db.execute(patient_query).scalar_one_or_none()
        return existing_patient is None

    def create_address(self, db, payload: dict) -> Address:
        address = Address(**payload)
        db.add(address)
        db.flush()
        return address

    def create_patient(self, db, payload: dict) -> Patient:
        patient = Patient(**payload)
        db.add(patient)
        db.flush()
        return patient

    def assign_doctor_to_patient(self, db, doctor_id: int, patient_id: int) -> None:
        assign_doctor_to_patient(db, doctor_id, patient_id)

    def create_encounter(
            self,
            db,
            *,
            patient_id: int,
            doctor_id: int | None,
            encounter_type: str,
            chief_complaint: str,
            created_at: datetime | None = None,
    ) -> None:
        db.add(
            Encounter(
                patient_id=patient_id,
                doctor_id=doctor_id,
                encounter_type=encounter_type,
                chief_complaint=chief_complaint,
                created_at=created_at or now_utc(),
            )
        )

    def create_admission_history(
            self,
            db,
            *,
            patient_id: int,
            doctor_id: int,
            entry_type: str,
            reason: str | None,
            note: str | None,
            created_at: datetime,
    ) -> None:
        db.add(
            PatientAdmissionHistory(
                patient_id=patient_id,
                doctor_id=doctor_id,
                type=entry_type,
                reason=reason,
                note=note,
                created_at=created_at,
            )
        )

    def add_doctor_activity(
            self,
            db,
            *,
            doctor_id: int,
            patient_id: int,
            activity_type: str,
            title: str,
            description: str,
            status: str,
            scheduled_at: datetime | None,
            created_at: datetime | None = None,
    ) -> DoctorActivity | None:
        doctor = db.get(Doctor, doctor_id)
        patient = db.get(Patient, patient_id)
        if doctor is None or patient is None:
            print(
                f"Skipping activity creation: doctor={doctor_id} patient={patient_id} "
                "not found"
            )
            return None
        try:
            validate_activity_creation(db, doctor, patient)
        except ValidationError as error:
            print(f"Skipping activity creation: {error.code} for doctor={doctor_id} patient={patient_id}")
            return None

        activity = DoctorActivity(
            doctor_id=doctor_id,
            patient_id=patient_id,
            type=activity_type,
            title=title,
            description=description,
            status=status,
            scheduled_at=scheduled_at or now_utc(),
            created_at=created_at or now_utc(),
        )
        db.add(activity)
        return activity

    def create_patient_diagnosis(
            self,
            db,
            *,
            patient_id: int,
            doctor_id: int,
            diagnosis: str,
            status: str,
            notes: str | None = None,
            created_at: datetime,
    ) -> None:
        normalized_status = self._sanitize_diagnosis_status(status)
        db.add(
            PatientDiagnosis(
                patient_id=patient_id,
                doctor_id=doctor_id,
                diagnosis=diagnosis,
                notes=notes,
                status=normalized_status,
                created_at=created_at,
                updated_at=created_at,
            )
        )

    def get_or_create_condition(self, db, name: str, status: str) -> PatientCondition:
        condition = db.execute(select(PatientCondition).where(PatientCondition.name == name)).scalar_one_or_none()
        if condition is not None:
            condition.status = self._sanitize_condition_status(condition.status)
            return condition

        condition = PatientCondition(name=name, status=self._sanitize_condition_status(status))
        db.add(condition)
        db.flush()
        return condition

    def has_condition_assignment(self, db, *, patient_id: int, condition_id: int) -> bool:
        assignment = db.execute(
            select(PatientConditionAssignment).where(
                PatientConditionAssignment.patient_id == patient_id,
                PatientConditionAssignment.condition_id == condition_id,
            )
        ).scalar_one_or_none()
        return assignment is not None

    def create_condition_assignment(
            self,
            db,
            *,
            patient_id: int,
            condition_id: int,
            doctor_id: int,
            status: str,
            diagnosed_at: datetime,
    ) -> None:
        normalized_status = self._sanitize_condition_status(status)
        db.add(
            PatientConditionAssignment(
                patient_id=patient_id,
                condition_id=condition_id,
                doctor_id=doctor_id,
                status=normalized_status,
                diagnosed_at=diagnosed_at,
                created_at=diagnosed_at,
            )
        )

    def create_patient_medication(
            self,
            db,
            *,
            patient_id: int,
            doctor_id: int,
            name: str,
            dosage: str,
            frequency: str,
            created_at: datetime,
    ) -> PatientMedication | None:
        clamped_name = self._clamp_text(name, self.MEDICATION_NAME_MAX_LENGTH)
        clamped_dosage = self._clamp_text(dosage, self.MEDICATION_DOSAGE_MAX_LENGTH)
        clamped_frequency = self._clamp_text(frequency, self.MEDICATION_FREQUENCY_MAX_LENGTH)

        existing = db.execute(
            select(PatientMedication)
            .where(
                PatientMedication.patient_id == patient_id,
                func.lower(PatientMedication.name) == clamped_name.strip().lower(),
                func.lower(PatientMedication.dosage) == clamped_dosage.strip().lower(),
                func.lower(PatientMedication.frequency) == clamped_frequency.strip().lower(),
                PatientMedication.created_at <= created_at,
            )
            .order_by(PatientMedication.created_at.desc(), PatientMedication.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return None

        medication = PatientMedication(
            patient_id=patient_id,
            doctor_id=doctor_id,
            name=clamped_name,
            dosage=clamped_dosage,
            frequency=clamped_frequency,
            created_at=created_at,
        )
        db.add(medication)
        db.flush()
        return medication

    def get_patient_medications(self, db, *, patient_id: int) -> list[PatientMedication]:
        return db.execute(
            select(PatientMedication)
            .where(PatientMedication.patient_id == patient_id)
            .order_by(PatientMedication.created_at.desc(), PatientMedication.id.desc())
        ).scalars().all()

    def get_latest_medication_by_name(
            self,
            db,
            *,
            patient_id: int,
            name: str,
            event_time: datetime,
    ) -> PatientMedication | None:
        return db.execute(
            select(PatientMedication)
            .where(
                PatientMedication.patient_id == patient_id,
                func.lower(PatientMedication.name) == name.strip().lower(),
                PatientMedication.created_at <= event_time,
            )
            .order_by(PatientMedication.created_at.desc(), PatientMedication.id.desc())
        ).scalar_one_or_none()

    def update_patient_medication_plan(
            self,
            db,
            *,
            medication: PatientMedication,
            doctor_id: int,
            dosage: str,
            frequency: str,
            updated_at: datetime,
            note: str | None = None,
            notes: str | None = None,
    ) -> PatientMedication:
        clamped_dosage = self._clamp_text(dosage, self.MEDICATION_DOSAGE_MAX_LENGTH)
        clamped_frequency = self._clamp_text(frequency, self.MEDICATION_FREQUENCY_MAX_LENGTH)

        medication.doctor_id = doctor_id
        medication.dosage = clamped_dosage
        medication.frequency = clamped_frequency
        medication.updated_at = updated_at
        medication.last_updated_note = note
        if notes is not None:
            medication.notes = notes
        return medication

    def create_patient_allergy(
            self,
            db,
            *,
            patient_id: int,
            doctor_id: int,
            allergy_name: str,
            severity: str,
            created_at: datetime,
    ) -> None:
        db.add(
            PatientAllergy(
                patient_id=patient_id,
                doctor_id=doctor_id,
                allergy_name=allergy_name,
                severity=severity,
                created_at=created_at,
            )
        )

    def get_patient(self, db, patient_id: int) -> Patient | None:
        return db.get(Patient, patient_id)

    def get_admitted_patients_for_monitoring(
            self,
            db,
            *,
            exclude_patient_ids: set[int],
            limit: int,
    ) -> list[Patient]:
        query = select(Patient).where(Patient.is_discharged.is_(False))
        if exclude_patient_ids:
            query = query.where(Patient.id.notin_(exclude_patient_ids))
        return db.execute(query.order_by(Patient.id.desc()).limit(limit)).scalars().all()

    def get_patient_condition_names(self, db, patient_id: int) -> list[str]:
        return db.execute(
            select(PatientCondition.name)
            .join(PatientConditionAssignment, PatientConditionAssignment.condition_id == PatientCondition.id)
            .where(PatientConditionAssignment.patient_id == patient_id)
            .order_by(PatientConditionAssignment.diagnosed_at.desc(), PatientConditionAssignment.id.desc())
        ).scalars().all()

    def get_patient_diagnosis_names(self, db, patient_id: int) -> list[str]:
        return db.execute(
            select(PatientDiagnosis.diagnosis)
            .where(PatientDiagnosis.patient_id == patient_id)
            .order_by(PatientDiagnosis.created_at.desc(), PatientDiagnosis.id.desc())
        ).scalars().all()

    def cancel_incoming_patient_activities(self, db, patient_id: int) -> None:
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

    def mark_patient_discharged(self, db, patient: Patient, reason: str, discharged_at: datetime | None = None) -> None:
        self.cancel_incoming_patient_activities(db, patient.id)
        patient.is_discharged = True
        patient.discharge_date = discharged_at or now_utc()
        patient.discharge_reason = reason

    def resolve_all_patient_diagnoses(self, db, *, patient_id: int, updated_at: datetime) -> int:
        diagnoses = db.execute(
            select(PatientDiagnosis).where(PatientDiagnosis.patient_id == patient_id)
        ).scalars().all()
        updated = 0
        for diagnosis in diagnoses:
            if diagnosis.status != "resolved":
                diagnosis.status = "resolved"
                diagnosis.updated_at = updated_at
                updated += 1
        return updated

    def resolve_patient_diagnoses_after_recovery_discharge(
            self,
            db,
            *,
            patient_id: int,
            updated_at: datetime,
            status_note: str,
            doctor_id: int | None = None,
    ) -> int:
        diagnoses = db.execute(
            select(PatientDiagnosis).where(PatientDiagnosis.patient_id == patient_id)
        ).scalars().all()
        updated = 0
        for diagnosis in diagnoses:
            changed = False
            if diagnosis.status != "resolved":
                diagnosis.status = "resolved"
                changed = True
            if (diagnosis.status_note or "").strip() != status_note.strip():
                diagnosis.status_note = status_note
                changed = True
            if changed:
                if doctor_id is not None:
                    diagnosis.doctor_id = doctor_id
                diagnosis.updated_at = updated_at
                updated += 1
        return updated

    def resolve_all_patient_conditions(self, db, *, patient_id: int, updated_at: datetime) -> int:
        assignments = db.execute(
            select(PatientConditionAssignment).where(PatientConditionAssignment.patient_id == patient_id)
        ).scalars().all()
        updated = 0
        for assignment in assignments:
            if assignment.status != "resolved":
                assignment.status = "resolved"
                assignment.updated_at = updated_at
                updated += 1
        return updated

    def update_condition_to_improving_after_positive_treatment(
            self,
            db,
            *,
            patient_id: int,
            updated_at: datetime,
            note: str,
            doctor_id: int | None = None,
    ) -> int:
        assignments = db.execute(
            select(PatientConditionAssignment).where(PatientConditionAssignment.patient_id == patient_id)
        ).scalars().all()
        updated = 0
        for assignment in assignments:
            if assignment.status == "resolved":
                continue
            changed = False
            if assignment.status != "improving":
                assignment.status = "improving"
                changed = True
            if (assignment.notes or "").strip() != note.strip():
                assignment.notes = note
                changed = True
            if changed:
                if doctor_id is not None:
                    assignment.doctor_id = doctor_id
                assignment.updated_at = updated_at
                updated += 1
        return updated

    # Backward-compatible alias used by older call sites.
    def update_condition_to_improving_after_effective_treatment(
            self,
            db,
            *,
            patient_id: int,
            updated_at: datetime,
            note: str,
            doctor_id: int | None = None,
    ) -> int:
        return self.update_condition_to_improving_after_positive_treatment(
            db,
            patient_id=patient_id,
            updated_at=updated_at,
            note=note,
            doctor_id=doctor_id,
        )

    def reconcile_after_ineffective_treatment(
            self,
            db,
            *,
            patient_id: int,
            updated_at: datetime,
            doctor_id: int | None = None,
            condition_note: str | None = None,
    ) -> dict[str, int]:
        condition_updates = 0

        assignments = db.execute(
            select(PatientConditionAssignment).where(PatientConditionAssignment.patient_id == patient_id)
        ).scalars().all()
        for assignment in assignments:
            changed = False
            if assignment.status in {"resolved", "improving"}:
                assignment.status = "active"
                changed = True
            if condition_note is not None and (assignment.notes or "").strip() != condition_note.strip():
                assignment.notes = condition_note
                changed = True
            if changed:
                if doctor_id is not None:
                    assignment.doctor_id = doctor_id
                assignment.updated_at = updated_at
                condition_updates += 1

        return {
            "diagnosis_updates": 0,
            "condition_updates": condition_updates,
        }

    def resolve_patient_conditions_after_recovery_discharge(
            self,
            db,
            *,
            patient_id: int,
            updated_at: datetime,
            note: str,
            doctor_id: int | None = None,
    ) -> int:
        assignments = db.execute(
            select(PatientConditionAssignment).where(PatientConditionAssignment.patient_id == patient_id)
        ).scalars().all()
        updated = 0
        for assignment in assignments:
            changed = False
            if assignment.status != "resolved":
                assignment.status = "resolved"
                changed = True
            if (assignment.notes or "").strip() != note.strip():
                assignment.notes = note
                changed = True
            if changed:
                if doctor_id is not None:
                    assignment.doctor_id = doctor_id
                assignment.updated_at = updated_at
                updated += 1
        return updated

    def get_first_assigned_doctor_id(self, db, patient_id: int) -> int | None:
        link = db.execute(
            doctor_activity_patients.select().where(doctor_activity_patients.c.patient_id == patient_id)
        ).first()
        return link.doctor_id if link else None

    def get_assigned_doctor_ids(self, db, patient_id: int) -> list[int]:
        links = db.execute(
            doctor_activity_patients.select().where(doctor_activity_patients.c.patient_id == patient_id)
        ).all()
        doctor_ids = [int(link.doctor_id) for link in links if getattr(link, "doctor_id", None) is not None]
        # Stable de-duplication while preserving insertion order.
        return list(dict.fromkeys(doctor_ids))

    def count_incoming_activities(self, db, patient_id: int) -> int:
        return (
            db.query(DoctorActivity)
            .filter(
                DoctorActivity.patient_id == patient_id,
                DoctorActivity.status == "incoming",
            )
            .count()
        )

    def doctor_has_incoming_activities(self, db, doctor_id: int) -> bool:
        return (
            db.query(DoctorActivity)
            .filter(
                DoctorActivity.doctor_id == doctor_id,
                DoctorActivity.status == "incoming",
            )
            .count()
        ) > 0

    def get_assigned_doctors_for_patient_department(self, db, patient_id: int, department: str) -> list[Doctor]:
        links = db.execute(
            doctor_activity_patients.select().where(doctor_activity_patients.c.patient_id == patient_id)
        ).all()

        valid_doctors: list[Doctor] = []
        for link in links:
            doctor = db.get(Doctor, link.doctor_id)
            if doctor and doctor.specialization == department:
                valid_doctors.append(doctor)

        return valid_doctors

    def create_vital(self, db, patient_id: int, vitals: dict, *, recorded_at: datetime | None = None) -> Vital:
        vital = Vital(patient_id=patient_id, recorded_at=recorded_at or now_utc(), **vitals)
        db.add(vital)
        db.flush()
        return vital

    def block_post_discharge_vital_and_alert_generation(self, db, patient_id: int) -> bool:
        patient = db.get(Patient, patient_id)
        if patient is None:
            print(f"Blocking clinical event generation: patient {patient_id} does not exist")
            return True
        if patient.is_discharged:
            print(f"Blocking clinical event generation: patient {patient_id} is discharged")
            return True
        return False

    def create_vital_safe(self, db, patient_id: int, vitals: dict, *, recorded_at: datetime | None = None) -> Vital | None:
        if self.block_post_discharge_vital_and_alert_generation(db, patient_id):
            return None
        return self.create_vital(db, patient_id, vitals, recorded_at=recorded_at)

    def create_alert(
            self,
            db,
            *,
            patient_id: int,
            vital_id: int,
            alert_type: str,
            message: str,
            severity: str,
            created_at: datetime | None = None,
    ) -> Alert | None:
        if patient_id is None:
            return None

        if self.block_post_discharge_vital_and_alert_generation(db, patient_id):
            return None

        alert = Alert(
            patient_id=patient_id,
            vital_id=vital_id,
            alert_type=alert_type,
            message=message,
            severity=severity,
            created_at=created_at or now_utc(),
        )
        db.add(alert)
        db.flush()
        return alert

    def cleanup_invalid_alerts(self, db) -> int:
        invalid_alert_ids = db.execute(
            select(Alert.id)
            .outerjoin(Patient, Patient.id == Alert.patient_id)
            .where((Alert.patient_id.is_(None)) | (Patient.id.is_(None)))
        ).scalars().all()
        if not invalid_alert_ids:
            return 0

        deleted = (
            db.query(Alert)
            .filter(Alert.id.in_(invalid_alert_ids))
            .delete(synchronize_session=False)
        )
        return int(deleted or 0)

    def normalize_medical_statuses(self, db) -> int:
        updated = 0

        diagnoses = db.query(PatientDiagnosis).all()
        for diagnosis in diagnoses:
            normalized = self._sanitize_diagnosis_status(diagnosis.status)
            if diagnosis.status != normalized:
                diagnosis.status = normalized
                updated += 1

        conditions = db.query(PatientCondition).all()
        for condition in conditions:
            normalized = self._sanitize_condition_status(condition.status)
            if condition.status != normalized:
                condition.status = normalized
                updated += 1

        assignments = db.query(PatientConditionAssignment).all()
        for assignment in assignments:
            normalized = self._sanitize_condition_status(assignment.status)
            if assignment.status != normalized:
                assignment.status = normalized
                updated += 1

        return updated

    def remove_patient_assignments(self, db, patient_id: int) -> None:
        db.execute(doctor_activity_patients.delete().where(doctor_activity_patients.c.patient_id == patient_id))
