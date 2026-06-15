from __future__ import annotations

import hashlib
import math
import random
import re
from datetime import date, datetime, timedelta

from passlib.context import CryptContext

from app.repositories import medical_repository
from app.repositories.patient_repository import PatientRepository
from app.simulator.buffers.buffers import SimulatorBuffers
from app.simulator.config.simulator_config import SimulatorConfig
from app.simulator.generators.activity_generator import generate_activity
from app.simulator.generators.doctor_generator import generate_doctor_payloads
from app.simulator.generators.patient_generator import (
    choose_medication_profile,
    generate_address,
    generate_patient_identity,
    generate_patient_profile,
    generate_phone_candidate,
)
from app.simulator.logic.activity_logic import (
    create_critical_flow,
    create_warning_flow,
    random_activity_probability_for_state,
)
from app.alerts.vital_alerts import build_transition_alerts, classify_vital_states
from app.simulator.logic.patient_state_logic import evaluate_patient_state, handle_state_transition
from app.simulator.logic.transfer_logic import transfer_patient
from app.simulator.messaging.kafka_producer import SimulatorKafkaProducer
from app.simulator.repositories.simulator_repository import SimulatorRepository
from app.utils.datetime import now_utc

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALERT_SEVERITY_SCORE = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "normal": 0,
}

BASE_LOOKBACK_DAYS_RANGE = (30, 730)
VITAL_STEP_MINUTES_RANGE = (4, 12)
ACTIVITY_STEP_HOURS_RANGE = (6, 48)
MEDICATION_STEP_DAYS_RANGE = (5, 28)
MAX_OUTCOME_HISTORY = 400
TREATMENT_EVALUATION_WINDOW_CYCLES = 6
TREATMENT_FAILURE_ALERT_CYCLES = 3
TREATMENT_MIN_SUCCESS_NORMAL_CYCLES = 2
MAX_TREATMENT_MEDICATIONS = 6
ALERT_COOLDOWN_MINUTES_RANGE = (5, 15)
MAX_ALERTS_PER_PATIENT_PER_HOUR = 18
MAX_ALERTS_PER_PATIENT_PER_CYCLE = 2
MAX_DOSAGE_MULTIPLIER = 4
MANUAL_PATIENT_DISCOVERY_LIMIT = 25
ALERT_DRIVEN_TRANSFER_TREATMENT_THRESHOLD = 9
MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE = 10
EFFECTIVE_DISCHARGE_TREATMENT_THRESHOLD = MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE
RECENT_OUTCOMES_REQUIRED = 2
DEBUG_FORCE_FREQUENT_ALERTS = True
DEBUG_ABNORMAL_VITAL_PROBABILITY = 0.08
DEBUG_ALERT_COOLDOWN_SECONDS_RANGE = (10, 20)
DEBUG_ALERT_BURST_TRIGGER_PROBABILITY = 0.05
DEBUG_ALERT_BURST_CYCLES_RANGE = (2, 4)
DEBUG_ALERT_BURST_ABNORMAL_PROBABILITY = 0.58
DEBUG_ALERT_BURST_COOLDOWN_SECONDS_RANGE = (4, 8)
STREAMING_ALERT_PROCESSING_LATENCY_MS_RANGE = (50, 500)
DEBUG_RECOVERED_DISCHARGE_LOGS = False
TREATMENT_ESCALATION_NOTE = "Treatment not working, patient got worse. Dose/frequency adjusted after persistent alerts."
SUCCESSFUL_RECOVERY_DISCHARGE_NOTE = (
    "Patient discharged after successful recovery: treatment remained effective across repeated updates, "
    "and all tracked diagnoses/conditions were resolved."
)
IMPROVING_CONDITION_NOTE = (
    "The patient condition was marked as improving because partial recovery was detected: "
    "at least one previously abnormal vital normalized after treatment."
)
RESOLVED_CONDITION_NOTE = (
    "The patient condition was marked as resolved because the final treatment outcome was effective "
    "and the patient recovered enough to be discharged."
)
RESOLVED_DIAGNOSIS_NOTE = (
    "The diagnosis was marked as resolved because the patient recovered after an effective final treatment "
    "outcome and was discharged."
)
INEFFECTIVE_TREATMENT_RECONCILE_CONDITION_NOTE = (
    "Condition status was reconciled to active because the latest treatment outcome is ineffective."
)
INITIAL_DIAGNOSIS_STATUSES = ("active", "chronic", "inactive")
INITIAL_CONDITION_STATUSES = ("active", "stable", "worsening", "critical", "chronic")
DEFAULT_SIMULATOR_DOCTOR_PASSWORD = "password123"
HARDCODED_DOCTOR_EMAIL = "hognogicristina@gmail.com"
HARDCODED_DOCTOR_PASSWORD = "lalalalalalL1"
RANDOM_DOCTOR_TARGET_COUNT = 49
HARDCODED_DOCTOR_PHONE = "+40755123456"
HARDCODED_DOCTOR_BIRTH_DATE = date(1988, 4, 12)
HARDCODED_DOCTOR_LICENSE = "STATIC-LIC-CH-00001"


class SimulatorService:
    def __init__(
            self,
            *,
            config: SimulatorConfig,
            buffers: SimulatorBuffers,
            repository: SimulatorRepository,
            producer: SimulatorKafkaProducer,
    ):
        self.config = config
        self.buffers = buffers
        self.repository = repository
        self.producer = producer
        self.active_patients: list[dict] = []
        self.counter = 1

    def _sample_streaming_alert_processing_delay(self) -> timedelta:
        min_ms, max_ms = STREAMING_ALERT_PROCESSING_LATENCY_MS_RANGE
        return timedelta(milliseconds=random.randint(min_ms, max_ms))

    def get_latest_vital_state(
            self,
            db,
            patient_id: int,
            *,
            up_to_timestamp: datetime | None = None,
    ):
        return PatientRepository.get_latest_vital_state(
            db,
            patient_id,
            up_to_timestamp=up_to_timestamp,
        )

    def get_latest_vital_alert_state(
            self,
            db,
            patient_id: int,
            *,
            up_to_timestamp: datetime | None = None,
    ):
        return PatientRepository.get_latest_vital_alert_state(
            db,
            patient_id,
            up_to_timestamp=up_to_timestamp,
        )

    def has_unresolved_abnormal_alerts_after(
            self,
            db,
            patient_id: int,
            timestamp: datetime,
            *,
            up_to_timestamp: datetime | None = None,
    ):
        return PatientRepository.has_unresolved_abnormal_alerts_after(
            db,
            patient_id,
            timestamp,
            up_to_timestamp=up_to_timestamp,
        )

    def can_discharge_patient_as_recovered(
            self,
            db,
            patient_id: int,
            final_treatment: dict | None,
            *,
            discharge_timestamp: datetime,
            stability_started_at: datetime | None,
    ):
        required_stability_window_seconds = max(1, TREATMENT_MIN_SUCCESS_NORMAL_CYCLES) * int(
            self.config.cycle_sleep_seconds
        )
        return PatientRepository.can_discharge_patient_as_recovered(
            db,
            patient_id,
            final_treatment,
            discharge_timestamp=discharge_timestamp,
            required_stability_window_seconds=required_stability_window_seconds,
            stability_started_at=stability_started_at,
            min_treatment_actions_required=MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE,
        )

    def block_post_discharge_vital_and_alert_generation(self, db, patient_id: int) -> bool:
        return self.repository.block_post_discharge_vital_and_alert_generation(db, patient_id)

    @staticmethod
    def _log_recovered_discharge_attempt(*, patient, allowed: bool, reason: str, debug_payload: dict) -> None:
        if not DEBUG_RECOVERED_DISCHARGE_LOGS:
            return
        print(
            "[RECOVERED_DISCHARGE_ATTEMPT] "
            f"patient_id={patient.id} "
            f"patient_name={patient.last_name} {patient.first_name} "
            f"allowed={allowed} "
            f"reason={reason} "
            f"payload={debug_payload}"
        )

    def initialize(self) -> None:
        departments = medical_repository.get_all_departments()
        if not departments:
            return

        with self.repository.session_scope() as db:
            self.repository.cleanup_invalid_alerts(db)
            self.repository.normalize_medical_statuses(db)
            reserved_phones: set[str] = set()

            random_password_hash = pwd_context.hash(DEFAULT_SIMULATOR_DOCTOR_PASSWORD)
            hardcoded_password_hash = pwd_context.hash(HARDCODED_DOCTOR_PASSWORD)

            hardcoded_doctor = self.repository.get_doctor_by_email_or_license(
                db,
                email=HARDCODED_DOCTOR_EMAIL,
                license_number=HARDCODED_DOCTOR_LICENSE,
            )
            if hardcoded_doctor is None:
                hardcoded_phone = self._resolve_unique_phone_for_doctor(
                    db,
                    preferred=HARDCODED_DOCTOR_PHONE,
                    reserved=reserved_phones,
                )
                self.repository.create_doctor(
                    db,
                    {
                        "first_name": "Cristina",
                        "last_name": "Hognogi",
                        "email": HARDCODED_DOCTOR_EMAIL,
                        "password_hash": hardcoded_password_hash,
                        "specialization": departments[0],
                        "license_number": HARDCODED_DOCTOR_LICENSE,
                        "phone_number": hardcoded_phone,
                        "birth_date": HARDCODED_DOCTOR_BIRTH_DATE,
                        "email_confirmed": True,
                        "is_active": True,
                    },
                )
            else:
                hardcoded_doctor.first_name = "Cristina"
                hardcoded_doctor.last_name = "Hognogi"
                hardcoded_doctor.password_hash = hardcoded_password_hash
                hardcoded_doctor.is_active = True
                if not hardcoded_doctor.pending_email:
                    hardcoded_doctor.email_confirmed = True
                hardcoded_doctor.birth_date = hardcoded_doctor.birth_date or HARDCODED_DOCTOR_BIRTH_DATE
                hardcoded_doctor.phone_number = self._resolve_unique_phone_for_doctor(
                    db,
                    preferred=hardcoded_doctor.phone_number or HARDCODED_DOCTOR_PHONE,
                    reserved=reserved_phones,
                    exclude_doctor_id=hardcoded_doctor.id,
                )

            random_payloads = generate_doctor_payloads(
                count=RANDOM_DOCTOR_TARGET_COUNT,
                departments=departments,
                password_hash=random_password_hash,
            )
            current_doctor_count = self.repository.get_doctor_count(db)
            random_slots = max(0, 50 - current_doctor_count)

            created_random = 0
            for payload in random_payloads:
                existing_doctor = self.repository.get_doctor_by_email_or_license(
                    db,
                    email=payload["email"],
                    license_number=payload["license_number"],
                )
                if existing_doctor is not None:
                    existing_doctor.birth_date = existing_doctor.birth_date or payload.get("birth_date") or self._generate_doctor_birth_date()
                    existing_doctor.phone_number = self._resolve_unique_phone_for_doctor(
                        db,
                        preferred=existing_doctor.phone_number or payload.get("phone_number"),
                        reserved=reserved_phones,
                        exclude_doctor_id=existing_doctor.id,
                    )
                    continue

                if created_random >= random_slots:
                    continue

                payload["phone_number"] = self._resolve_unique_phone_for_doctor(
                    db,
                    preferred=payload.get("phone_number"),
                    reserved=reserved_phones,
                )
                payload["birth_date"] = payload.get("birth_date") or self._generate_doctor_birth_date()
                self.repository.create_doctor(db, payload)
                created_random += 1

    def run_cycle(self) -> None:
        with self.repository.session_scope() as db:
            self.repository.cleanup_invalid_alerts(db)
            self.repository.normalize_medical_statuses(db)
            activities_created_in_cycle: set[int] = set()

            self._discover_existing_patients(db)

            if random.random() < self.config.patient_spawn_probability:
                patient_data = self._create_patient(db, self.counter)
                if patient_data is not None:
                    db.commit()
                    self.active_patients.append(patient_data)
                    self.counter += 1

            if not self.active_patients:
                return

            next_active_patients: list[dict] = []
            for patient_data in self.active_patients:
                should_keep = self._process_patient(db, patient_data, activities_created_in_cycle)
                if should_keep:
                    next_active_patients.append(patient_data)

            self.active_patients = next_active_patients

    def _discover_existing_patients(self, db) -> None:
        active_patient_ids = {
            int(patient_data["id"])
            for patient_data in self.active_patients
            if patient_data.get("id") is not None
        }
        patients = self.repository.get_admitted_patients_for_monitoring(
            db,
            exclude_patient_ids=active_patient_ids,
            limit=MANUAL_PATIENT_DISCOVERY_LIMIT,
        )
        for patient in patients:
            patient_data = self._build_patient_monitoring_state(db, patient)
            if patient_data is not None:
                self.active_patients.append(patient_data)
                active_patient_ids.add(patient.id)

    def _build_patient_monitoring_state(self, db, patient) -> dict | None:
        drugs = medical_repository.get_all_medications()
        dosages = medical_repository.get_all_dosages()
        frequencies = medical_repository.get_all_frequencies()
        if not drugs:
            return None

        doctor_id = self.repository.get_first_assigned_doctor_id(db, patient.id)
        if doctor_id is None:
            doctor = self.repository.get_random_doctor_for_department(db, patient.department)
            if doctor is not None:
                self.repository.assign_doctor_to_patient(db, doctor.id, patient.id)

        condition_name, preferred_medication = self._resolve_monitoring_profile(db, patient, drugs)
        medication_plan = self._build_medication_plan(
            drugs=drugs,
            condition_name=condition_name,
            is_pregnant=bool(patient.is_pregnant),
            preferred_medication=preferred_medication,
        )
        if not medication_plan:
            return None

        now = now_utc()
        segment = "active"
        treatment_state = self._initialize_treatment_state(
            patient_id=patient.id,
            condition_name=condition_name,
            medication_plan=medication_plan,
        )
        clinical_state = self._initial_clinical_state(
            patient_id=patient.id,
            segment=segment,
            condition_name=condition_name,
        )

        return {
            "id": patient.id,
            "condition": condition_name,
            "diagnosis": None,
            "segment": segment,
            "base_time": now,
            "admission_date": now,
            "timeline_cursor": now,
            "last_alert_evaluation": {"count": 0, "severity_score": 0},
            "recent_treatment_outcomes": [],
            "last_vital_alert_states": {"heart_rate": "normal", "oxygen": "normal", "temperature": "normal"},
            "last_alert_timestamp": None,
            "recent_alert_timestamps": [],
            "alert_cooldown_minutes": random.randint(*ALERT_COOLDOWN_MINUTES_RANGE),
            "medication_dosage": self._default_dosage_for_patient(dosages, patient.id),
            "medication_frequency": self._default_frequency_for_patient(frequencies, patient.id),
            "treatment_state": treatment_state,
            "clinical_state": clinical_state,
            "stability_started_at": None,
            "high_critical_alert_count": 0,
            "alert_driven_treatment_count": 0,
            "treatment_update_count": 0,
            "total_alert_count": 0,
            "latest_treatment_outcome": None,
            "pending_treatment_outcome_since": None,
            "monitoring_status": "active",
            "debug_alert_cooldown_seconds": random.randint(*DEBUG_ALERT_COOLDOWN_SECONDS_RANGE),
            "debug_alert_burst_cycles_remaining": 0,
        }

    def _resolve_monitoring_profile(self, db, patient, drugs: list[dict]) -> tuple[str, str | None]:
        condition_names = [
            str(item).strip()
            for item in self.repository.get_patient_condition_names(db, patient.id)
            if str(item).strip()
        ]
        diagnosis_names = [
            str(item).strip()
            for item in self.repository.get_patient_diagnosis_names(db, patient.id)
            if str(item).strip()
        ]
        medications = self.repository.get_patient_medications(db, patient_id=patient.id)
        preferred_medication = next((str(item.name).strip() for item in medications if str(item.name).strip()), None)

        known_drug_conditions = {
            (drug.get("condition") or "").strip().lower(): (drug.get("condition") or "").strip()
            for drug in drugs
            if (drug.get("condition") or "").strip()
        }
        for candidate in [*condition_names, *diagnosis_names]:
            normalized = candidate.lower()
            if normalized in known_drug_conditions:
                return known_drug_conditions[normalized], preferred_medication

        profile = choose_medication_profile(drugs, bool(patient.is_pregnant))
        if profile is None:
            fallback_condition = condition_names[0] if condition_names else "General monitoring"
            return fallback_condition, preferred_medication

        return profile["condition_name"], preferred_medication or profile["medication_name"]

    def _create_patient(self, db, index: int) -> dict | None:
        counties = medical_repository.get_all_counties()
        drugs = medical_repository.get_all_medications()
        diagnoses = medical_repository.get_all_diagnoses()
        conditions = medical_repository.get_all_conditions()
        allergies = medical_repository.get_all_allergies()
        dosages = medical_repository.get_all_dosages()
        frequencies = medical_repository.get_all_frequencies()
        if not counties or not drugs or not diagnoses or not conditions or not dosages or not frequencies:
            return None

        doctor = self.repository.get_random_doctor(db)
        if doctor is None:
            return None

        identity = generate_patient_identity(index, doctor.specialization)
        address_payload = generate_address(counties)
        medication_profile = choose_medication_profile(drugs, identity["is_pregnant"])
        if medication_profile is None:
            return None
        medication_plan = self._build_medication_plan(
            drugs=drugs,
            condition_name=medication_profile["condition_name"],
            is_pregnant=identity["is_pregnant"],
            preferred_medication=medication_profile["medication_name"],
        )
        if not medication_plan:
            return None

        now = now_utc()
        base_time = self._generate_base_time(now)
        segment = self._pick_patient_segment()
        admission_date = self._build_admission_date(base_time=base_time, now=now, segment=segment)

        diagnosis_seed = next(
            (label for label in diagnoses if medication_profile["condition_name"].lower() in label.lower()),
            None,
        )

        address = self.repository.create_address(db, address_payload)
        patient = self.repository.create_patient(
            db,
            {
                **identity,
                "phone_number": self._generate_unique_phone(db),
                "discharge_date": None,
                "discharge_reason": None,
                "address_id": address.id,
            },
        )

        self.repository.assign_doctor_to_patient(db, doctor.id, patient.id)
        self.repository.create_encounter(
            db,
            patient_id=patient.id,
            doctor_id=doctor.id,
            encounter_type="admission",
            chief_complaint="Auto generated",
            created_at=admission_date,
        )
        self.repository.create_admission_history(
            db,
            patient_id=patient.id,
            doctor_id=doctor.id,
            entry_type="admission",
            reason=None,
            note=self._admission_note_from_arrival_method(patient.arrival_method),
            created_at=admission_date,
        )

        if patient.is_pregnant:
            pregnancy_doctors = self.repository.get_assigned_doctors_for_patient_department(db, patient.id, patient.department)
            if pregnancy_doctors:
                pregnancy_doctor = random.choice(pregnancy_doctors)
                scheduled_at = self._clamp_to_now(admission_date + timedelta(days=1))
                self.repository.add_doctor_activity(
                    db,
                    doctor_id=pregnancy_doctor.id,
                    patient_id=patient.id,
                    activity_type="PROCEDURE",
                    title="Childbirth preparation",
                    description="Pregnancy monitoring and delivery planning",
                    status="incoming",
                    scheduled_at=scheduled_at,
                    created_at=admission_date + timedelta(hours=2),
                )

        self._seed_patient_clinical_records(
            db,
            patient_id=patient.id,
            doctor_id=doctor.id,
            base_condition=medication_profile["condition_name"],
            diagnosis_seed=diagnosis_seed,
            medication_name=medication_profile["medication_name"],
            base_time=base_time,
            admission_date=admission_date,
            now=now,
            all_conditions=conditions,
            all_diagnoses=diagnoses,
            all_allergies=allergies,
            dosages=dosages,
            frequencies=frequencies,
        )

        treatment_state = self._initialize_treatment_state(
            patient_id=patient.id,
            condition_name=medication_profile["condition_name"],
            medication_plan=medication_plan,
        )
        clinical_state = self._initial_clinical_state(
            patient_id=patient.id,
            segment=segment,
            condition_name=medication_profile["condition_name"],
        )

        patient_data = {
            "id": patient.id,
            "condition": medication_profile["condition_name"],
            "diagnosis": diagnosis_seed,
            "segment": segment,
            "base_time": base_time,
            "admission_date": admission_date,
            "timeline_cursor": admission_date,
            "last_alert_evaluation": {"count": 0, "severity_score": 0},
            "recent_treatment_outcomes": [],
            "last_vital_alert_states": {"heart_rate": "normal", "oxygen": "normal", "temperature": "normal"},
            "last_alert_timestamp": None,
            "recent_alert_timestamps": [],
            "alert_cooldown_minutes": random.randint(*ALERT_COOLDOWN_MINUTES_RANGE),
            "medication_dosage": self._default_dosage_for_patient(dosages, patient.id),
            "medication_frequency": self._default_frequency_for_patient(frequencies, patient.id),
            "treatment_state": treatment_state,
            "clinical_state": clinical_state,
            "stability_started_at": None,
            "high_critical_alert_count": 0,
            "alert_driven_treatment_count": 0,
            "treatment_update_count": 0,
            "total_alert_count": 0,
            "latest_treatment_outcome": None,
            "pending_treatment_outcome_since": None,
            "monitoring_status": "active",
            "debug_alert_cooldown_seconds": random.randint(*DEBUG_ALERT_COOLDOWN_SECONDS_RANGE),
            "debug_alert_burst_cycles_remaining": 0,
        }

        self._seed_historical_activities(db, patient, patient_data)
        self._seed_historical_vitals_and_alerts(db, patient, patient_data)

        return patient_data

    def _seed_patient_clinical_records(
            self,
            db,
            *,
            patient_id: int,
            doctor_id: int,
            base_condition: str,
            diagnosis_seed: str | None,
            medication_name: str,
            base_time: datetime,
            admission_date: datetime,
            now: datetime,
            all_conditions: list[str],
            all_diagnoses: list[str],
            all_allergies: list[str],
            dosages: list[str],
            frequencies: list[str],
    ) -> None:
        profile = generate_patient_profile(
            base_condition=base_condition,
            diagnosis_seed=diagnosis_seed,
            all_conditions=all_conditions,
            all_diagnoses=all_diagnoses,
            all_allergies=all_allergies,
            dosages=dosages,
            frequencies=frequencies,
        )

        diagnosis_cursor = max(base_time, admission_date - timedelta(days=random.randint(5, 30)))
        for diagnosis in profile["diagnoses"]:
            diagnosis_cursor = self._advance_time(diagnosis_cursor, timedelta(days=1), timedelta(days=12))
            diagnosed_at = self._clamp_to_now(diagnosis_cursor)
            self.repository.create_patient_diagnosis(
                db,
                patient_id=patient_id,
                doctor_id=doctor_id,
                diagnosis=diagnosis,
                status=random.choice(INITIAL_DIAGNOSIS_STATUSES),
                notes=f"Simulated clinical assessment for {diagnosis}.",
                created_at=diagnosed_at,
            )

        condition_cursor = max(base_time, admission_date - timedelta(days=random.randint(3, 20)))
        for label in profile["conditions"]:
            condition = self.repository.get_or_create_condition(
                db,
                name=label,
                status=random.choice(INITIAL_CONDITION_STATUSES),
            )
            if self.repository.has_condition_assignment(db, patient_id=patient_id, condition_id=condition.id):
                continue

            condition_cursor = self._advance_time(condition_cursor, timedelta(days=1), timedelta(days=10))
            diagnosed_at = self._clamp_to_now(condition_cursor)
            self.repository.create_condition_assignment(
                db,
                patient_id=patient_id,
                condition_id=condition.id,
                doctor_id=doctor_id,
                status=random.choice(INITIAL_CONDITION_STATUSES),
                diagnosed_at=diagnosed_at,
            )

        medication_cursor = max(admission_date, base_time)
        medication_count = random.randint(2, 5)
        medication_candidates = [
            medication_name,
            *random.sample(profile.get("medications", []), k=min(2, len(profile.get("medications", [])))),
        ]
        for medication_index in range(medication_count):
            medication_cursor = self._advance_time(
                medication_cursor,
                timedelta(days=MEDICATION_STEP_DAYS_RANGE[0]),
                timedelta(days=MEDICATION_STEP_DAYS_RANGE[1]),
            )
            created_at = self._clamp_to_now(medication_cursor)
            if created_at >= now:
                break

            selected_medication = medication_candidates[min(medication_index, len(medication_candidates) - 1)]
            self.repository.create_patient_medication(
                db,
                patient_id=patient_id,
                doctor_id=doctor_id,
                name=selected_medication,
                dosage=profile["dosage"],
                frequency=profile["frequency"],
                created_at=created_at,
            )

        allergy_cursor = base_time
        for allergy in profile["allergies"]:
            allergy_cursor = self._advance_time(allergy_cursor, timedelta(days=7), timedelta(days=45))
            created_at = self._clamp_to_now(allergy_cursor)
            self.repository.create_patient_allergy(
                db,
                patient_id=patient_id,
                doctor_id=doctor_id,
                allergy_name=allergy,
                severity=random.choice(["mild", "moderate", "severe"]),
                created_at=created_at,
            )

    def _seed_historical_activities(self, db, patient, patient_data: dict) -> None:
        doctors = self.repository.get_assigned_doctors_for_patient_department(db, patient.id, patient.department)
        if not doctors:
            return

        doctor = random.choice(doctors)
        now = now_utc()
        base_time = patient_data["base_time"]
        activity_cursor = max(base_time, patient_data["admission_date"])
        segment = patient_data["segment"]

        completed_count = random.randint(2, 5)
        for _ in range(completed_count):
            activity_cursor = self._advance_time(
                activity_cursor,
                timedelta(hours=ACTIVITY_STEP_HOURS_RANGE[0]),
                timedelta(hours=ACTIVITY_STEP_HOURS_RANGE[1]),
            )
            created_at = self._clamp_to_now(activity_cursor)
            scheduled_at = self._clamp_to_now(created_at + timedelta(hours=random.randint(1, 6)))
            self.repository.add_doctor_activity(
                db,
                doctor_id=doctor.id,
                patient_id=patient.id,
                activity_type=random.choice(["Consultation", "Procedure", "Lab test"]),
                title="Follow-up care",
                description="Scheduled follow-up based on patient progression",
                status="completed",
                scheduled_at=scheduled_at,
                created_at=created_at,
            )

        if segment in {"active", "critical"}:
            incoming_count = 1 if segment == "active" else random.randint(2, 3)
            for _ in range(incoming_count):
                created_at = self._clamp_to_now(now - timedelta(hours=random.randint(1, 48)))
                scheduled_at = self._clamp_to_now(created_at + timedelta(hours=random.randint(1, 12)))
                self.repository.add_doctor_activity(
                    db,
                    doctor_id=doctor.id,
                    patient_id=patient.id,
                    activity_type=random.choice(["Procedure", "Consultation", "Lab test", "Surgery"]),
                    title="Pending intervention",
                    description="Queued based on latest patient evolution",
                    status="incoming",
                    scheduled_at=scheduled_at,
                    created_at=created_at,
                )
        else:
            canceled_created_at = self._clamp_to_now(now - timedelta(days=random.randint(2, 15)))
            self.repository.add_doctor_activity(
                db,
                doctor_id=doctor.id,
                patient_id=patient.id,
                activity_type="Consultation",
                title="Canceled reassessment",
                description="No longer needed due to recovery progression",
                status="canceled",
                scheduled_at=canceled_created_at,
                created_at=canceled_created_at,
            )

    def _seed_historical_vitals_and_alerts(self, db, patient, patient_data: dict) -> None:
        # Keep the patient timeline aligned with real-time emission.
        # Historical backfill rows are intentionally skipped so the simulator never emits
        # vitals/alerts with past timestamps.
        patient_data["timeline_cursor"] = now_utc()

    def _process_patient(self, db, patient_data: dict, activities_created_in_cycle: set[int]) -> bool:
        patient_id = patient_data.get("id")
        if patient_id is None:
            return False

        patient = self.repository.get_patient(db, patient_id)
        if patient is None or patient.is_discharged:
            return False
        if self.block_post_discharge_vital_and_alert_generation(db, patient_id):
            return False

        alert_processing_delay = self._sample_streaming_alert_processing_delay()
        alert_created_at = now_utc()
        event_time = alert_created_at - alert_processing_delay
        patient_data["timeline_cursor"] = event_time

        vitals = self._generate_vitals_for_patient(patient_data)
        vital = self.repository.create_vital_safe(db, patient.id, vitals, recorded_at=event_time)
        if vital is None:
            return False

        self.buffers.append_vital_sample(patient.id, vitals)

        new_state = evaluate_patient_state(vitals)
        _, transitioned_state = handle_state_transition(patient.id, new_state, self.buffers.patient_states)

        if transitioned_state == "critical":
            self._handle_critical_flow(db, patient, activities_created_in_cycle, reference_time=event_time)
        elif transitioned_state == "warning":
            self._handle_warning_flow(db, patient, activities_created_in_cycle, reference_time=event_time)

        alert_stats = self._create_alerts(
            db,
            patient.id,
            vital.id,
            vitals,
            patient_data=patient_data,
            recorded_at=event_time,
            alert_created_at=alert_created_at,
        )
        high_or_critical_count = int(alert_stats.get("high_or_critical_count", 0))
        if high_or_critical_count > 0:
            patient_data["high_critical_alert_count"] = int(patient_data.get("high_critical_alert_count", 0)) + high_or_critical_count
        has_abnormal_vitals = self._has_abnormal_vitals(vitals)
        self._record_outcome_evaluation(
            db,
            patient_id=patient.id,
            patient_data=patient_data,
            recorded_at=event_time,
            vitals=vitals,
        )
        self._update_stability_tracking(
            patient_data=patient_data,
            current_state=new_state,
            event_time=event_time,
        )
        discharged_for_transfer = self._update_treatment_lifecycle(
            db,
            patient=patient,
            patient_data=patient_data,
            has_abnormal_vitals=has_abnormal_vitals,
            current_state=new_state,
            event_time=event_time,
            allow_discharge=True,
        )
        self._apply_treatment_effect_to_clinical_state(
            patient_data,
            has_escalated_alert=bool(alert_stats.get("high_or_critical_count")),
        )
        if discharged_for_transfer:
            return False

        if self.buffers.should_stream_patient_vitals(patient.id):
            self.producer.send_vital(
                {
                    "event": "vital",
                    "patient_id": patient.id,
                    "recorded_at": event_time.isoformat(),
                    **vitals,
                }
            )

        probability = random_activity_probability_for_state(
            new_state,
            self.config.base_random_activity_probability,
            self.config.random_activity_state_multiplier or {},
        )
        if random.random() < probability:
            self._maybe_generate_random_activity(
                db,
                patient_id=patient.id,
                patient_department=patient.department,
                source_condition=patient_data.get("condition"),
                source_diagnosis=patient_data.get("diagnosis"),
                activities_created_in_cycle=activities_created_in_cycle,
                reference_time=event_time,
            )

        if not patient.is_discharged:
            self._handle_stable_flow(db, patient, patient_data, current_state=new_state, event_time=event_time)

        return not patient.is_discharged

    def _handle_critical_flow(self, db, patient, activities_created_in_cycle: set[int], *, reference_time: datetime) -> None:
        if not self._can_create_patient_activity(db, patient.id, activities_created_in_cycle):
            return

        if patient.is_discharged:
            return

        doctors = self.repository.get_assigned_doctors_for_patient_department(db, patient.id, patient.department)
        if not doctors:
            self._transfer_patient(db, patient, reference_time=reference_time)
            return
        doctor = random.choice(doctors)

        activity = create_critical_flow(reference_time)
        created_activity = self.repository.add_doctor_activity(
            db,
            doctor_id=doctor.id,
            patient_id=patient.id,
            activity_type=activity["type"],
            title=activity["title"],
            description=activity["description"],
            status=activity["status"],
            scheduled_at=self._clamp_to_now(activity["scheduled_at"]),
            created_at=reference_time,
        )
        if created_activity is not None:
            self.buffers.mark_activity_created(patient.id, activities_created_in_cycle)

    def _handle_warning_flow(self, db, patient, activities_created_in_cycle: set[int], *, reference_time: datetime) -> None:
        if not self._can_create_patient_activity(db, patient.id, activities_created_in_cycle):
            return

        if patient.is_discharged:
            return

        doctors = self.repository.get_assigned_doctors_for_patient_department(db, patient.id, patient.department)
        if not doctors:
            return
        doctor = random.choice(doctors)

        activity = create_warning_flow(reference_time)
        created_activity = self.repository.add_doctor_activity(
            db,
            doctor_id=doctor.id,
            patient_id=patient.id,
            activity_type=activity["type"],
            title=activity["title"],
            description=activity["description"],
            status=activity["status"],
            scheduled_at=self._clamp_to_now(activity["scheduled_at"]),
            created_at=reference_time,
        )
        if created_activity is not None:
            self.buffers.mark_activity_created(patient.id, activities_created_in_cycle)

    def _handle_stable_flow(self, db, patient, patient_data: dict, *, current_state: str, event_time: datetime) -> None:
        if current_state != "stable":
            return
        if not self._is_effective_outcome_ready_for_discharge(patient_data=patient_data):
            return
        self._discharge_due_to_effective_treatment(
            db,
            patient=patient,
            patient_data=patient_data,
            event_time=event_time,
        )

    def _transfer_patient(self, db, patient, *, reference_time: datetime) -> None:
        assigned_doctors = self.repository.get_assigned_doctors_for_patient_department(db, patient.id, patient.department)
        if any(self.repository.doctor_has_incoming_activities(db, doctor.id) for doctor in assigned_doctors):
            return

        departments = medical_repository.get_all_departments()
        candidate_departments = [dept for dept in departments if dept != patient.department]
        if not candidate_departments:
            return

        new_department = random.choice(candidate_departments)
        new_doctor = self.repository.get_random_doctor_for_department(db, new_department)
        if new_doctor is None:
            return

        transfer_details = transfer_patient(new_department)
        patient.department = transfer_details["new_department"]

        self.repository.remove_patient_assignments(db, patient.id)
        self.repository.assign_doctor_to_patient(db, new_doctor.id, patient.id)

        activity = transfer_details["activity"]
        self.repository.add_doctor_activity(
            db,
            doctor_id=new_doctor.id,
            patient_id=patient.id,
            activity_type=activity["type"],
            title=activity["title"],
            description=activity["description"],
            status=activity["status"],
            scheduled_at=activity["scheduled_at"],
            created_at=reference_time,
        )

    def _create_alerts(
            self,
            db,
            patient_id: int,
            vital_id: int,
            vitals: dict,
            *,
            patient_data: dict,
            recorded_at: datetime,
            alert_created_at: datetime,
            emit_events: bool = True,
            include_buffer: bool = True,
    ) -> dict:
        patient = self.repository.get_patient(db, patient_id)
        if patient is None or getattr(patient, "id", None) is None:
            return {
                "count": 0,
                "severity_score": 0,
                "high_or_critical_count": 0,
                "highest_severity": "normal",
            }
        if self.block_post_discharge_vital_and_alert_generation(db, patient_id):
            return {
                "count": 0,
                "severity_score": 0,
                "high_or_critical_count": 0,
                "highest_severity": "normal",
            }

        count = 0
        severity_score = 0
        high_or_critical_count = 0
        highest_severity = "normal"
        generated_in_cycle = 0

        previous_states = patient_data.get("last_vital_alert_states") or {"heart_rate": "normal", "oxygen": "normal", "temperature": "normal"}
        current_states = classify_vital_states(vitals)

        transition_alerts = build_transition_alerts(
            previous_states=previous_states,
            current_states=current_states,
            vitals=vitals,
        )

        if (not DEBUG_FORCE_FREQUENT_ALERTS) and not transition_alerts:
            return {
                "count": 0,
                "severity_score": 0,
                "high_or_critical_count": 0,
                "highest_severity": "normal",
            }

        recent_alert_timestamps = [
            ts
            for ts in (patient_data.get("recent_alert_timestamps") or [])
            if isinstance(ts, datetime) and recorded_at - ts <= timedelta(hours=1)
        ]
        patient_data["recent_alert_timestamps"] = recent_alert_timestamps

        if len(recent_alert_timestamps) >= MAX_ALERTS_PER_PATIENT_PER_HOUR:
            return {
                "count": 0,
                "severity_score": 0,
                "high_or_critical_count": 0,
                "highest_severity": "normal",
            }

        if DEBUG_FORCE_FREQUENT_ALERTS:
            burst_cycles_remaining = int(patient_data.get("debug_alert_burst_cycles_remaining", 0))
            if burst_cycles_remaining > 0:
                cooldown_seconds = random.randint(*DEBUG_ALERT_BURST_COOLDOWN_SECONDS_RANGE)
            else:
                cooldown_seconds = int(patient_data.get("debug_alert_cooldown_seconds", DEBUG_ALERT_COOLDOWN_SECONDS_RANGE[0]))
            cooldown = timedelta(seconds=max(1, cooldown_seconds))
        else:
            cooldown_minutes = int(patient_data.get("alert_cooldown_minutes", ALERT_COOLDOWN_MINUTES_RANGE[0]))
            cooldown = timedelta(minutes=max(1, cooldown_minutes))
        last_alert_timestamp = patient_data.get("last_alert_timestamp")
        if isinstance(last_alert_timestamp, datetime) and recorded_at - last_alert_timestamp < cooldown:
            return {
                "count": 0,
                "severity_score": 0,
                "high_or_critical_count": 0,
                "highest_severity": "normal",
            }

        def create_alert(*, alert_type: str, severity: str, message: str) -> None:
            nonlocal count, severity_score, high_or_critical_count, highest_severity, generated_in_cycle
            if generated_in_cycle >= MAX_ALERTS_PER_PATIENT_PER_CYCLE:
                return
            if len(recent_alert_timestamps) >= MAX_ALERTS_PER_PATIENT_PER_HOUR:
                return

            created_alert = self.repository.create_alert(
                db,
                patient_id=patient_id,
                vital_id=vital_id,
                alert_type=alert_type,
                message=message,
                severity=severity,
                created_at=alert_created_at,
            )
            if created_alert is None:
                return

            if emit_events:
                self.producer.send_alert(
                    {
                        "event": "alert",
                        "id": created_alert.id,
                        "patient_id": created_alert.patient_id,
                        "vital_id": created_alert.vital_id,
                        "alert_type": created_alert.alert_type,
                        "severity": created_alert.severity,
                        "message": created_alert.message,
                        "created_at": created_alert.created_at.isoformat(),
                    }
                )

            if include_buffer:
                self.buffers.append_alert_sample(patient_id, alert_type)
            generated_in_cycle += 1
            recent_alert_timestamps.append(alert_created_at)
            patient_data["last_alert_timestamp"] = alert_created_at

            if severity in {"high", "critical"}:
                count += 1
                severity_score += ALERT_SEVERITY_SCORE.get(severity, 0)
                high_or_critical_count += 1
            if ALERT_SEVERITY_SCORE.get(severity, 0) > ALERT_SEVERITY_SCORE.get(highest_severity, 0):
                highest_severity = severity

        for transition_alert in transition_alerts:
            create_alert(
                alert_type=transition_alert.alert_type,
                severity=transition_alert.severity,
                message=transition_alert.message,
            )

        patient_data["recent_alert_timestamps"] = recent_alert_timestamps
        patient_data["last_vital_alert_states"] = current_states
        if generated_in_cycle > 0:
            patient_data["total_alert_count"] = int(patient_data.get("total_alert_count", 0)) + generated_in_cycle

        return {
            "count": count,
            "severity_score": severity_score,
            "high_or_critical_count": high_or_critical_count,
            "highest_severity": highest_severity,
            "generated_count": generated_in_cycle,
        }

    def _record_outcome_evaluation(
            self,
            db,
            *,
            patient_id: int,
            patient_data: dict,
            recorded_at: datetime,
            vitals: dict,
    ) -> None:
        latest_treatment = PatientRepository.get_latest_treatment_action_outcome(db, patient_id)
        latest_outcome = str((latest_treatment or {}).get("outcome") or "").strip().lower()
        if latest_outcome not in {"effective", "improving", "ineffective"}:
            latest_outcome = "effective" if not self._has_abnormal_vitals(vitals) else "ineffective"
        outcome = latest_outcome
        recent = patient_data.setdefault("recent_treatment_outcomes", [])
        recent.append(outcome)
        if len(recent) > RECENT_OUTCOMES_REQUIRED:
            del recent[:-RECENT_OUTCOMES_REQUIRED]
        patient_data["latest_treatment_outcome"] = outcome
        patient_data["pending_treatment_outcome_since"] = None

    def _build_medication_plan(
            self,
            *,
            drugs: list[dict],
            condition_name: str,
            is_pregnant: bool,
            preferred_medication: str | None,
    ) -> list[str]:
        allowed_categories = {"A", "B"} if is_pregnant else {"A", "B", "C", "D", "N"}
        condition_key = (condition_name or "").strip().lower()

        condition_matches: set[str] = set()
        fallback_matches: set[str] = set()
        for drug in drugs:
            medication = (drug.get("medication") or "").strip()
            category = (drug.get("pregnancy_category") or "").strip()
            if not medication or category not in allowed_categories:
                continue
            fallback_matches.add(medication)
            if (drug.get("condition") or "").strip().lower() == condition_key:
                condition_matches.add(medication)

        ordered_medications = sorted(condition_matches or fallback_matches)
        preferred = (preferred_medication or "").strip()
        if preferred:
            ordered_medications = [preferred, *[item for item in ordered_medications if item != preferred]]

        return ordered_medications[:MAX_TREATMENT_MEDICATIONS]

    @staticmethod
    def _default_dosage_for_patient(dosages: list[str], patient_id: int) -> str:
        if not dosages:
            return "1x standard dose"
        dosage = dosages[patient_id % len(dosages)]
        return f"1x {dosage}"

    @staticmethod
    def _default_frequency_for_patient(frequencies: list[str], patient_id: int) -> str:
        if not frequencies:
            return "Daily"
        return frequencies[(patient_id * 3) % len(frequencies)]

    @staticmethod
    def _initialize_treatment_state(*, patient_id: int, condition_name: str, medication_plan: list[str]) -> dict:
        return {
            "patient_id": patient_id,
            "condition_name": condition_name,
            "medication_plan": medication_plan,
            "active_medication_index": None,
            "active_medication_name": None,
            "active_started_at": None,
            "cycles_on_medication": 0,
            "abnormal_cycles_on_medication": 0,
            "normal_cycles_on_medication": 0,
            "evaluation_window_cycles": TREATMENT_EVALUATION_WINDOW_CYCLES,
            "status": "pending",
            "effect_profile": None,
            "history": [],
        }

    @staticmethod
    def _normalize_medication_name(value: str | None) -> str:
        return (value or "").strip().lower()

    @staticmethod
    def _increase_dosage(dosage: str) -> str:
        text = (dosage or "").strip()
        if not text:
            return "2x standard dose"

        match = re.match(r"^\s*(\d+)\s*x\s*(.+)\s*$", text, re.IGNORECASE)
        if match:
            current = max(1, int(match.group(1)))
            next_value = min(MAX_DOSAGE_MULTIPLIER, current + 1)
            return f"{next_value}x {match.group(2).strip()}"

        return f"2x {text}"

    @staticmethod
    def _increase_frequency(frequency: str) -> str:
        text = (frequency or "").strip()
        if not text:
            return "once daily"

        mapped = {
            "once daily": "twice daily",
            "daily": "twice daily",
            "every 24h": "twice daily",
            "every 24 hours": "twice daily",
            "twice daily": "every 8 hours",
            "every 12h": "every 8 hours",
            "every 12 hours": "every 8 hours",
            "every 8h": "every 6 hours",
            "every 8 hours": "every 6 hours",
            "every 6h": "every 4 hours",
            "every 6 hours": "every 4 hours",
            "weekly": "once daily",
        }
        return mapped.get(text.lower(), text)

    def _plan_medication_adjustment(self, *, dosage: str, frequency: str) -> tuple[str, str]:
        if random.random() < 0.5:
            return self._increase_dosage(dosage), frequency
        return dosage, self._increase_frequency(frequency)

    def _choose_replacement_medication(self, db, *, patient, patient_data: dict) -> tuple[int, str] | None:
        treatment = patient_data.get("treatment_state") or {}
        medication_plan = treatment.get("medication_plan") or []
        if not medication_plan:
            return None

        used_names = {
            self._normalize_medication_name(entry.get("medication"))
            for entry in (treatment.get("history") or [])
            if isinstance(entry, dict)
        }
        for medication in self.repository.get_patient_medications(db, patient_id=patient.id):
            used_names.add(self._normalize_medication_name(medication.name))

        candidates: list[tuple[int, str]] = []
        for index, medication_name in enumerate(medication_plan):
            normalized = self._normalize_medication_name(medication_name)
            if normalized and normalized not in used_names:
                candidates.append((index, medication_name))

        if not candidates:
            return None
        return random.choice(candidates)

    def _initial_clinical_state(self, *, patient_id: int, segment: str, condition_name: str) -> dict:
        base_severity_by_segment = {
            "discharge_candidate": 26.0,
            "active": 54.0,
            "critical": 82.0,
        }
        base = base_severity_by_segment.get(segment, 54.0)
        offset = self._deterministic_centered_value(patient_id, condition_name, "baseline", amplitude=6.0)
        phase = self._deterministic_fraction(patient_id, condition_name, "phase") * 20.0
        return {
            "severity_index": self._clamp_float(base + offset, 5.0, 98.0),
            "cycle_index": 0,
            "oscillation_phase": phase,
        }

    def _update_stability_tracking(self, *, patient_data: dict, current_state: str, event_time: datetime) -> None:
        if current_state == "stable":
            if not isinstance(patient_data.get("stability_started_at"), datetime):
                patient_data["stability_started_at"] = event_time
            return
        patient_data["stability_started_at"] = None

    def _update_treatment_lifecycle(
            self,
            db,
            *,
            patient,
            patient_data: dict,
            has_abnormal_vitals: bool,
            current_state: str,
            event_time: datetime,
            allow_discharge: bool,
    ) -> bool:
        treatment = patient_data.get("treatment_state")
        if not isinstance(treatment, dict):
            return False

        if treatment.get("active_medication_name") is None and has_abnormal_vitals:
            started = self._start_treatment(
                db,
                patient=patient,
                patient_data=patient_data,
                medication_index=0,
                event_time=event_time,
            )
            if not started:
                treatment["status"] = "exhausted"
                if allow_discharge and self._should_transfer_for_persistent_instability(patient_data=patient_data):
                    return self._transfer_due_to_alert_driven_treatments(
                        db,
                        patient=patient,
                        patient_data=patient_data,
                        event_time=event_time,
                    )
                return False

        if treatment.get("active_medication_name") is None:
            return False

        previous_treatment_status = str(treatment.get("status") or "").strip().lower()
        latest_outcome = str(patient_data.get("latest_treatment_outcome") or "").strip().lower()
        treatment["cycles_on_medication"] = int(treatment.get("cycles_on_medication", 0)) + 1
        if has_abnormal_vitals:
            treatment["abnormal_cycles_on_medication"] = int(treatment.get("abnormal_cycles_on_medication", 0)) + 1
        else:
            treatment["normal_cycles_on_medication"] = int(treatment.get("normal_cycles_on_medication", 0)) + 1

        if latest_outcome in {"effective", "improving"} and previous_treatment_status not in {"effective", "improving"}:
            self._mark_conditions_improving_after_positive_outcome(
                db,
                patient_id=patient.id,
                event_time=event_time,
            )

        if current_state == "stable" and not has_abnormal_vitals:
            treatment["status"] = "effective"
            if self._is_effective_outcome_ready_for_discharge(patient_data=patient_data):
                return self._discharge_due_to_effective_treatment(
                    db,
                    patient=patient,
                    patient_data=patient_data,
                    event_time=event_time,
                )

        cycles_on_medication = int(treatment.get("cycles_on_medication", 0))
        evaluation_window = max(1, int(treatment.get("evaluation_window_cycles", TREATMENT_EVALUATION_WINDOW_CYCLES)))
        if cycles_on_medication < evaluation_window:
            return False

        abnormal_cycles = int(treatment.get("abnormal_cycles_on_medication", 0))
        if abnormal_cycles >= TREATMENT_FAILURE_ALERT_CYCLES:
            treatment["status"] = "ineffective"
            preferred_doctor_id = self._latest_treatment_doctor_id(db, patient=patient, patient_data=patient_data, event_time=event_time)
            assigned_doctor_id = self._select_status_change_doctor_id(
                db,
                patient_id=patient.id,
                preferred_doctor_id=preferred_doctor_id,
            )
            self.repository.reconcile_after_ineffective_treatment(
                db,
                patient_id=patient.id,
                updated_at=event_time,
                doctor_id=assigned_doctor_id,
                condition_note=INEFFECTIVE_TREATMENT_RECONCILE_CONDITION_NOTE,
            )
            if assigned_doctor_id is None:
                return False
            current_dosage = str(patient_data.get("medication_dosage") or "1x standard dose")
            current_frequency = str(patient_data.get("medication_frequency") or "Daily")

            if random.random() < 0.5:
                next_dosage, next_frequency = self._plan_medication_adjustment(
                    dosage=current_dosage,
                    frequency=current_frequency,
                )
                adjusted = self._adjust_existing_treatment(
                    db,
                    patient=patient,
                    patient_data=patient_data,
                    doctor_id=assigned_doctor_id,
                    event_time=event_time,
                    next_dosage=next_dosage,
                    next_frequency=next_frequency,
                )
                if adjusted:
                    treatment["status"] = "adjusted"
                    treatment["cycles_on_medication"] = 0
                    treatment["abnormal_cycles_on_medication"] = 0
                    treatment["normal_cycles_on_medication"] = 0
                    if self._should_transfer_for_persistent_instability(patient_data=patient_data):
                        return self._transfer_due_to_alert_driven_treatments(
                            db,
                            patient=patient,
                            patient_data=patient_data,
                            event_time=event_time,
                        )
                    return False

            replacement = self._choose_replacement_medication(db, patient=patient, patient_data=patient_data)
            if replacement is not None:
                next_index, _ = replacement
                switched = self._start_treatment(
                    db,
                    patient=patient,
                    patient_data=patient_data,
                    medication_index=next_index,
                    event_time=event_time,
                    doctor_id=assigned_doctor_id,
                    escalation_note=TREATMENT_ESCALATION_NOTE,
                )
                if switched:
                    if self._should_transfer_for_persistent_instability(patient_data=patient_data):
                        return self._transfer_due_to_alert_driven_treatments(
                            db,
                            patient=patient,
                            patient_data=patient_data,
                            event_time=event_time,
                        )
                    return False

            treatment["status"] = "exhausted"
            if allow_discharge and self._should_transfer_for_persistent_instability(patient_data=patient_data):
                return self._transfer_due_to_alert_driven_treatments(
                    db,
                    patient=patient,
                    patient_data=patient_data,
                    event_time=event_time,
                )
            return False

        normal_cycles = int(treatment.get("normal_cycles_on_medication", 0))
        if normal_cycles >= TREATMENT_MIN_SUCCESS_NORMAL_CYCLES and current_state == "stable":
            treatment["status"] = "effective"
            if self._is_effective_outcome_ready_for_discharge(patient_data=patient_data):
                return self._discharge_due_to_effective_treatment(
                    db,
                    patient=patient,
                    patient_data=patient_data,
                    event_time=event_time,
                )

        return False

    def _mark_conditions_improving_after_positive_outcome(self, db, *, patient_id: int, event_time: datetime) -> int:
        doctor_id = self._select_status_change_doctor_id(db, patient_id=patient_id)
        return self.repository.update_condition_to_improving_after_positive_treatment(
            db,
            patient_id=patient_id,
            updated_at=event_time,
            note=IMPROVING_CONDITION_NOTE,
            doctor_id=doctor_id,
        )

    def _is_effective_outcome_ready_for_discharge(self, *, patient_data: dict) -> bool:
        treatment_updates = int(patient_data.get("treatment_update_count", 0))
        if treatment_updates < MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE:
            return False

        recent_outcomes = [str(item).strip().lower() for item in (patient_data.get("recent_treatment_outcomes") or [])]
        if len(recent_outcomes) < RECENT_OUTCOMES_REQUIRED:
            return False
        if any(outcome != "effective" for outcome in recent_outcomes[-RECENT_OUTCOMES_REQUIRED:]):
            return False

        if str((patient_data.get("monitoring_status") or "active")).lower() == "transferred":
            return False

        return True

    def _discharge_due_to_effective_treatment(self, db, *, patient, patient_data: dict, event_time: datetime) -> bool:
        if patient.is_discharged:
            return False
        if str((patient_data.get("monitoring_status") or "active")).lower() == "transferred":
            return False

        final_treatment = PatientRepository.get_latest_treatment_action_outcome(db, patient.id)
        can_discharge, reason_code, debug_payload = self.can_discharge_patient_as_recovered(
            db,
            patient.id,
            final_treatment,
            discharge_timestamp=event_time,
            stability_started_at=patient_data.get("stability_started_at"),
        )
        self._log_recovered_discharge_attempt(
            patient=patient,
            allowed=can_discharge,
            reason=reason_code,
            debug_payload=debug_payload,
        )
        if not can_discharge:
            return False

        preferred_doctor_id = self._latest_treatment_doctor_id(db, patient=patient, patient_data=patient_data, event_time=event_time)
        doctor_id = self._select_status_change_doctor_id(
            db,
            patient_id=patient.id,
            preferred_doctor_id=preferred_doctor_id,
        )
        self.repository.resolve_patient_diagnoses_after_recovery_discharge(
            db,
            patient_id=patient.id,
            updated_at=event_time,
            status_note=RESOLVED_DIAGNOSIS_NOTE,
            doctor_id=doctor_id,
        )
        self.repository.resolve_patient_conditions_after_recovery_discharge(
            db,
            patient_id=patient.id,
            updated_at=event_time,
            note=RESOLVED_CONDITION_NOTE,
            doctor_id=doctor_id,
        )
        self.repository.mark_patient_discharged(
            db,
            patient,
            "Recovered after effective treatment",
            event_time,
        )
        patient_data["monitoring_status"] = "discharged"

        if doctor_id is not None:
            self.repository.create_admission_history(
                db,
                patient_id=patient.id,
                doctor_id=doctor_id,
                entry_type="discharge",
                reason="Recovered after effective treatment",
                note=SUCCESSFUL_RECOVERY_DISCHARGE_NOTE,
                created_at=event_time,
            )

        self.producer.send_discharge(
            {
                "event": "discharge",
                "patient_id": patient.id,
                "reason": "Recovered after effective treatment",
                "note": SUCCESSFUL_RECOVERY_DISCHARGE_NOTE,
                "trigger": "effective_outcome_treatment_threshold",
                "treatment_count": int(patient_data.get("treatment_update_count", 0)),
                "alert_count": int(patient_data.get("total_alert_count", 0)),
                "created_at": event_time.isoformat(),
            }
        )
        return True

    def _latest_treatment_doctor_id(self, db, *, patient, patient_data: dict, event_time: datetime) -> int | None:
        treatment = patient_data.get("treatment_state") or {}
        active_medication = str(treatment.get("active_medication_name") or "").strip()
        if not active_medication:
            return None

        latest = self.repository.get_latest_medication_by_name(
            db,
            patient_id=patient.id,
            name=active_medication,
            event_time=event_time,
        )
        if latest is None:
            return None
        return int(latest.doctor_id) if latest.doctor_id is not None else None

    def _select_status_change_doctor_id(
            self,
            db,
            *,
            patient_id: int,
            preferred_doctor_id: int | None = None,
    ) -> int | None:
        assigned_doctor_ids = self.repository.get_assigned_doctor_ids(db, patient_id)
        if preferred_doctor_id is not None and preferred_doctor_id in assigned_doctor_ids:
            return preferred_doctor_id
        if len(assigned_doctor_ids) == 1:
            return assigned_doctor_ids[0]
        if len(assigned_doctor_ids) > 1:
            return random.choice(assigned_doctor_ids)
        if preferred_doctor_id is not None:
            return preferred_doctor_id
        return self.repository.get_first_assigned_doctor_id(db, patient_id)

    def _transfer_due_to_alert_driven_treatments(
            self,
            db,
            *,
            patient,
            patient_data: dict,
            event_time: datetime,
    ) -> bool:
        if patient.is_discharged:
            return False
        if not self._latest_outcome_is_ineffective(patient_data):
            return False

        patient_data["monitoring_status"] = "transferred"
        self._discharge_as_transferred(db, patient, event_time=event_time)
        self.producer.send_transfer(
            {
                "event": "transfer",
                "patient_id": patient.id,
                "reason": "Transferred after persistent unstable vitals despite repeated treatment changes",
                "trigger": "persistent_unstable_vitals_threshold",
                "alert_count": int(patient_data.get("high_critical_alert_count", 0)),
                "treatment_count": int(patient_data.get("treatment_update_count", 0)),
                "created_at": event_time.isoformat(),
            }
        )
        return True

    def _should_transfer_for_persistent_instability(self, *, patient_data: dict) -> bool:
        treatment_updates = int(patient_data.get("treatment_update_count", 0))
        if treatment_updates < ALERT_DRIVEN_TRANSFER_TREATMENT_THRESHOLD:
            return False
        if not self._latest_outcome_is_ineffective(patient_data):
            return False
        recent_outcomes = [str(item).strip().lower() for item in (patient_data.get("recent_treatment_outcomes") or [])]
        if len(recent_outcomes) < RECENT_OUTCOMES_REQUIRED:
            return False
        return all(outcome == "ineffective" for outcome in recent_outcomes[-RECENT_OUTCOMES_REQUIRED:])

    @staticmethod
    def _latest_outcome_is_ineffective(patient_data: dict) -> bool:
        latest_outcome = str(patient_data.get("latest_treatment_outcome") or "").strip().lower()
        if latest_outcome:
            return latest_outcome == "ineffective"
        recent_outcomes = [str(item).strip().lower() for item in (patient_data.get("recent_treatment_outcomes") or [])]
        return bool(recent_outcomes) and recent_outcomes[-1] == "ineffective"

    @staticmethod
    def _has_abnormal_vitals(vitals: dict) -> bool:
        return (
                vitals["heart_rate"] > 110
                or vitals["oxygen_saturation"] < 92
                or vitals["temperature"] > 38
        )

    def _start_treatment(
            self,
            db,
            *,
            patient,
            patient_data: dict,
            medication_index: int,
            event_time: datetime,
            doctor_id: int | None = None,
            escalation_note: str | None = None,
    ) -> bool:
        treatment = patient_data.get("treatment_state")
        if not isinstance(treatment, dict):
            return False

        medication_plan = treatment.get("medication_plan") or []
        if medication_index < 0 or medication_index >= len(medication_plan):
            return False

        resolved_doctor_id = doctor_id if doctor_id is not None else self.repository.get_first_assigned_doctor_id(db, patient.id)
        if resolved_doctor_id is None:
            return False

        medication_name = medication_plan[medication_index]
        treatment_attempt = int(patient_data.get("treatment_update_count", 0)) + 1
        profile = self._build_effect_profile(
            patient_id=int(patient.id),
            condition_name=str(patient_data.get("condition") or treatment.get("condition_name") or ""),
            medication_name=medication_name,
            line_index=medication_index,
            treatment_attempt=treatment_attempt,
            current_severity=float((patient_data.get("clinical_state") or {}).get("severity_index", 50.0)),
        )

        treatment["active_medication_index"] = medication_index
        treatment["active_medication_name"] = medication_name
        treatment["active_started_at"] = event_time
        treatment["cycles_on_medication"] = 0
        treatment["abnormal_cycles_on_medication"] = 0
        treatment["normal_cycles_on_medication"] = 0
        treatment["status"] = "active"
        treatment["effect_profile"] = profile

        treatment_history = treatment.setdefault("history", [])
        treatment_history.append(
            {
                "medication": medication_name,
                "started_at": event_time,
                "effective_probability": profile["effectiveness_probability"],
                "effective": profile["effective"],
            }
        )
        patient_data["treatment_update_count"] = int(patient_data.get("treatment_update_count", 0)) + 1
        patient_data["pending_treatment_outcome_since"] = event_time
        patient_data["latest_treatment_outcome"] = None

        dosage = str(patient_data.get("medication_dosage") or "1x standard dose")
        frequency = str(patient_data.get("medication_frequency") or "Daily")
        existing_same_medication = self.repository.get_latest_medication_by_name(
            db,
            patient_id=patient.id,
            name=medication_name,
            event_time=event_time,
        )
        if existing_same_medication is not None:
            next_dosage, next_frequency = self._plan_medication_adjustment(
                dosage=dosage,
                frequency=frequency,
            )
            escalation_actor_note = None
            escalation_notes = None
            if escalation_note:
                escalation_actor_note = (
                    f"{escalation_note} Modified by doctor: "
                    f"{self._doctor_display_name(db, resolved_doctor_id)}"
                )
                escalation_notes = escalation_note
            self.repository.update_patient_medication_plan(
                db,
                medication=existing_same_medication,
                doctor_id=resolved_doctor_id,
                dosage=next_dosage,
                frequency=next_frequency,
                updated_at=event_time,
                note=escalation_actor_note,
                notes=escalation_notes,
            )
            patient_data["medication_dosage"] = next_dosage
            patient_data["medication_frequency"] = next_frequency
        else:
            self.repository.create_patient_medication(
                db,
                patient_id=patient.id,
                doctor_id=resolved_doctor_id,
                name=medication_name,
                dosage=dosage,
                frequency=frequency,
                created_at=event_time,
            )
            if escalation_note:
                latest = self.repository.get_latest_medication_by_name(
                    db,
                    patient_id=patient.id,
                    name=medication_name,
                    event_time=event_time,
                )
                if latest is not None:
                    self.repository.update_patient_medication_plan(
                        db,
                        medication=latest,
                        doctor_id=resolved_doctor_id,
                        dosage=latest.dosage,
                        frequency=latest.frequency,
                        updated_at=event_time,
                        note=(
                            f"{escalation_note} Modified by doctor: "
                            f"{self._doctor_display_name(db, resolved_doctor_id)}"
                        ),
                        notes=escalation_note,
                    )

        return True

    def _adjust_existing_treatment(
            self,
            db,
            *,
            patient,
            patient_data: dict,
            doctor_id: int,
            event_time: datetime,
            next_dosage: str,
            next_frequency: str,
    ) -> bool:
        treatment = patient_data.get("treatment_state") or {}
        active_medication = str(treatment.get("active_medication_name") or "").strip()
        if not active_medication:
            return False

        current_dosage = str(patient_data.get("medication_dosage") or "1x standard dose")
        current_frequency = str(patient_data.get("medication_frequency") or "Daily")
        if next_dosage == current_dosage and next_frequency == current_frequency:
            return False

        latest = self.repository.get_latest_medication_by_name(
            db,
            patient_id=patient.id,
            name=active_medication,
            event_time=event_time,
        )
        if latest is not None:
            self.repository.update_patient_medication_plan(
                db,
                medication=latest,
                doctor_id=doctor_id,
                dosage=next_dosage,
                frequency=next_frequency,
                updated_at=event_time,
                note=f"{TREATMENT_ESCALATION_NOTE} Modified by doctor: {self._doctor_display_name(db, doctor_id)}",
                notes=TREATMENT_ESCALATION_NOTE,
            )
        else:
            created = self.repository.create_patient_medication(
                db,
                patient_id=patient.id,
                doctor_id=doctor_id,
                name=active_medication,
                dosage=next_dosage,
                frequency=next_frequency,
                created_at=event_time,
            )
            if created is None:
                return False
            self.repository.update_patient_medication_plan(
                db,
                medication=created,
                doctor_id=doctor_id,
                dosage=next_dosage,
                frequency=next_frequency,
                updated_at=event_time,
                note=f"{TREATMENT_ESCALATION_NOTE} Modified by doctor: {self._doctor_display_name(db, doctor_id)}",
                notes=TREATMENT_ESCALATION_NOTE,
            )

        patient_data["medication_dosage"] = next_dosage
        patient_data["medication_frequency"] = next_frequency
        patient_data["treatment_update_count"] = int(patient_data.get("treatment_update_count", 0)) + 1
        patient_data["pending_treatment_outcome_since"] = event_time
        patient_data["latest_treatment_outcome"] = None
        return True

    def _doctor_display_name(self, db, doctor_id: int) -> str:
        doctor = self.repository.get_doctor(db, doctor_id)
        if doctor is None:
            return "--"
        return f"{doctor.last_name} {doctor.first_name}".strip()

    def _build_effect_profile(
            self,
            *,
            patient_id: int,
            condition_name: str,
            medication_name: str,
            line_index: int,
            treatment_attempt: int,
            current_severity: float,
    ) -> dict:
        line_penalty = min(0.12, line_index * 0.03)
        severity_penalty = min(0.16, max(0.0, (current_severity - 52.0) / 235.0))
        medication_bias = self._deterministic_centered_value(
            patient_id,
            condition_name,
            medication_name,
            "bias",
            amplitude=0.12,
        )

        if treatment_attempt <= 3:
            phase_base = 0.40
        elif treatment_attempt <= 7:
            phase_base = 0.67
        else:
            phase_base = 0.80 + min(0.12, max(0, treatment_attempt - 8) * 0.02)

        effectiveness_probability = self._clamp_float(
            phase_base - line_penalty - severity_penalty + medication_bias,
            0.26,
            0.95,
        )
        response_score = self._deterministic_fraction(
            patient_id,
            condition_name,
            medication_name,
            line_index,
            "response",
        )
        effective = response_score <= effectiveness_probability

        improvement_factor = 2.2 + self._deterministic_fraction(
            patient_id,
            condition_name,
            medication_name,
            line_index,
            "improvement",
        ) * 3.2
        failure_factor = 0.55 + self._deterministic_fraction(
            patient_id,
            condition_name,
            medication_name,
            line_index,
            "failure",
        ) * 1.45
        onset_cycles = 1 + int(
            self._deterministic_fraction(patient_id, medication_name, line_index, "onset") * 3
        )

        return {
            "effective": effective,
            "effectiveness_probability": effectiveness_probability,
            "improvement_factor": improvement_factor,
            "failure_factor": failure_factor,
            "onset_cycles": onset_cycles,
            "treatment_attempt": treatment_attempt,
        }

    def _apply_treatment_effect_to_clinical_state(self, patient_data: dict, *, has_escalated_alert: bool) -> None:
        clinical_state = patient_data.get("clinical_state")
        treatment_state = patient_data.get("treatment_state")
        if not isinstance(clinical_state, dict):
            return

        severity = float(clinical_state.get("severity_index", 50.0))
        if not isinstance(treatment_state, dict) or treatment_state.get("active_medication_name") is None:
            severity += 1.0 if has_escalated_alert else 0.25
            clinical_state["severity_index"] = self._clamp_float(severity, 5.0, 98.0)
            return

        profile = treatment_state.get("effect_profile") or {}
        cycles_on_medication = int(treatment_state.get("cycles_on_medication", 0))
        treatment_updates = int(patient_data.get("treatment_update_count", 0))
        progression_relief = min(2.4, max(0, treatment_updates - 3) * 0.28)
        onset_cycles = int(profile.get("onset_cycles", 2))
        improvement_factor = float(profile.get("improvement_factor", 2.0))
        failure_factor = float(profile.get("failure_factor", 1.2))
        effective = bool(profile.get("effective"))

        if effective:
            if cycles_on_medication >= onset_cycles:
                severity -= (improvement_factor + progression_relief)
            else:
                severity -= (improvement_factor * 0.45) + (progression_relief * 0.35)
        else:
            if cycles_on_medication >= onset_cycles:
                if treatment_updates >= 4:
                    severity += max(0.08, failure_factor - (progression_relief * 0.95))
                else:
                    severity += failure_factor
            else:
                if treatment_updates >= 4:
                    severity += max(0.05, (failure_factor * 0.5) - (progression_relief * 0.7))
                else:
                    severity += failure_factor * 0.45

        if has_escalated_alert:
            severity += 0.25
        else:
            severity -= 0.35

        clinical_state["severity_index"] = self._clamp_float(severity, 5.0, 98.0)

    def _discharge_as_transferred(self, db, patient, *, event_time: datetime) -> None:
        reason = "Transferred to another hospital"
        self.repository.mark_patient_discharged(db, patient, reason, event_time)

        doctor_id = self.repository.get_first_assigned_doctor_id(db, patient.id)
        if doctor_id is not None:
            self.repository.create_admission_history(
                db,
                patient_id=patient.id,
                doctor_id=doctor_id,
                entry_type="discharge",
                reason=reason,
                note=None,
                created_at=event_time,
            )

    def _generate_vitals_for_patient(self, patient_data: dict) -> dict:
        clinical_state = patient_data.get("clinical_state") or {}
        patient_id = int(patient_data.get("id", 0))
        severity = float(clinical_state.get("severity_index", 50.0))
        cycle_index = int(clinical_state.get("cycle_index", 0))
        phase = float(clinical_state.get("oscillation_phase", 0.0))
        wave = math.sin((cycle_index + phase) / 5.0)

        heart_rate = int(
            round(
                72.0
                + (severity * 0.74)
                + (wave * 2.2)
                + self._deterministic_centered_value(patient_id, cycle_index, "hr", amplitude=4.0)
            )
        )
        oxygen_saturation = int(
            round(
                99.0
                - (severity * 0.17)
                + (wave * 0.8)
                + self._deterministic_centered_value(patient_id, cycle_index, "spo2", amplitude=1.0)
            )
        )
        temperature = int(
            round(
                36.0
                + (severity * 0.04)
                + (wave * 0.3)
                + self._deterministic_centered_value(patient_id, cycle_index, "temp", amplitude=0.7)
            )
        )
        systolic_bp = int(
            round(
                108.0
                + (severity * 0.62)
                + (wave * 3.0)
                + self._deterministic_centered_value(patient_id, cycle_index, "sys", amplitude=5.0)
            )
        )
        diastolic_bp = int(
            round(
                66.0
                + (severity * 0.38)
                + (wave * 2.0)
                + self._deterministic_centered_value(patient_id, cycle_index, "dia", amplitude=4.0)
            )
        )

        clinical_state["cycle_index"] = cycle_index + 1
        patient_data["clinical_state"] = clinical_state

        if DEBUG_FORCE_FREQUENT_ALERTS:
            burst_cycles_remaining = int(patient_data.get("debug_alert_burst_cycles_remaining", 0))
            if burst_cycles_remaining <= 0 and random.random() < DEBUG_ALERT_BURST_TRIGGER_PROBABILITY:
                burst_cycles_remaining = random.randint(*DEBUG_ALERT_BURST_CYCLES_RANGE)
            abnormal_probability = (
                DEBUG_ALERT_BURST_ABNORMAL_PROBABILITY
                if burst_cycles_remaining > 0
                else DEBUG_ABNORMAL_VITAL_PROBABILITY
            )
            patient_data["debug_alert_burst_cycles_remaining"] = max(0, burst_cycles_remaining - 1)
        else:
            abnormal_probability = 0.0

        if DEBUG_FORCE_FREQUENT_ALERTS and random.random() < abnormal_probability:
            heart_rate = max(heart_rate, random.randint(124, 150))
            oxygen_saturation = min(oxygen_saturation, random.randint(82, 89))
            temperature = max(temperature, random.randint(39, 40))

        return {
            "heart_rate": self._clamp_int(heart_rate, 55, 170),
            "oxygen_saturation": self._clamp_int(oxygen_saturation, 75, 100),
            "temperature": self._clamp_int(temperature, 35, 41),
            "systolic_bp": self._clamp_int(systolic_bp, 90, 190),
            "diastolic_bp": self._clamp_int(diastolic_bp, 55, 120),
        }

    @staticmethod
    def _deterministic_fraction(*parts: object) -> float:
        key = "|".join(str(part) for part in parts)
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], "big")
        return value / float(2 ** 64 - 1)

    @classmethod
    def _deterministic_centered_value(cls, *parts: object, amplitude: float) -> float:
        return (cls._deterministic_fraction(*parts) - 0.5) * 2.0 * amplitude

    @staticmethod
    def _clamp_float(value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    @staticmethod
    def _clamp_int(value: int, min_value: int, max_value: int) -> int:
        return max(min_value, min(max_value, value))

    def _can_create_patient_activity(self, db, patient_id: int, activities_created_in_cycle: set[int]) -> bool:
        incoming_count = self.repository.count_incoming_activities(db, patient_id)
        return self.buffers.can_create_activity_for_patient(
            patient_id,
            incoming_count,
            activities_created_in_cycle,
        )

    def _maybe_generate_random_activity(
            self,
            db,
            *,
            patient_id: int,
            patient_department: str,
            source_condition: str | None,
            source_diagnosis: str | None,
            activities_created_in_cycle: set[int],
            reference_time: datetime,
    ) -> None:
        if not self._can_create_patient_activity(db, patient_id, activities_created_in_cycle):
            return

        patient = self.repository.get_patient(db, patient_id)
        if patient is None or patient.is_discharged:
            return

        doctors = self.repository.get_assigned_doctors_for_patient_department(db, patient_id, patient_department)
        if not doctors:
            return

        activity_types = medical_repository.get_all_activity_types()
        if not activity_types:
            return

        doctor = random.choice(doctors)
        activity_type = random.choice(activity_types)
        source = source_condition or source_diagnosis or "medical condition"
        activity = generate_activity(activity_type, source, reference_time=reference_time)

        created_activity = self.repository.add_doctor_activity(
            db,
            doctor_id=doctor.id,
            patient_id=patient_id,
            activity_type=activity["type"],
            title=activity["title"],
            description=activity["description"],
            status=activity["status"],
            scheduled_at=self._clamp_to_now(activity["scheduled_at"]),
            created_at=reference_time,
        )
        if created_activity is not None:
            self.buffers.mark_activity_created(patient_id, activities_created_in_cycle)

    def _generate_unique_phone(self, db) -> str:
        while True:
            candidate = generate_phone_candidate()
            if self.repository.is_phone_available(db, candidate):
                return candidate

    def _resolve_unique_phone_for_doctor(
            self,
            db,
            *,
            preferred: str | None,
            reserved: set[str],
            exclude_doctor_id: int | None = None,
    ) -> str:
        preferred_phone = (preferred or "").strip()
        if preferred_phone:
            normalized = preferred_phone.lower()
            if normalized not in reserved and self.repository.is_phone_available(
                    db,
                    preferred_phone,
                    exclude_doctor_id=exclude_doctor_id,
            ):
                reserved.add(normalized)
                return preferred_phone

        while True:
            candidate = generate_phone_candidate()
            normalized = candidate.lower()
            if normalized in reserved:
                continue
            if self.repository.is_phone_available(
                    db,
                    candidate,
                    exclude_doctor_id=exclude_doctor_id,
            ):
                reserved.add(normalized)
                return candidate

    @staticmethod
    def _generate_doctor_birth_date() -> date:
        return date.today() - timedelta(days=random.randint(30 * 365, 65 * 365))

    @staticmethod
    def _admission_note_from_arrival_method(arrival_method: str) -> str:
        if arrival_method == "ambulance":
            return "Arrived by ambulance"
        return "Arrived by themselves"

    @staticmethod
    def _generate_base_time(now: datetime) -> datetime:
        lookback_days = random.randint(*BASE_LOOKBACK_DAYS_RANGE)
        lookback_hours = random.randint(0, 23)
        lookback_minutes = random.randint(0, 59)
        return now - timedelta(days=lookback_days, hours=lookback_hours, minutes=lookback_minutes)

    @staticmethod
    def _pick_patient_segment() -> str:
        bucket = random.random()
        if bucket < 0.30:
            return "discharge_candidate"
        if bucket < 0.80:
            return "active"
        return "critical"

    def _build_admission_date(self, *, base_time: datetime, now: datetime, segment: str) -> datetime:
        if segment == "discharge_candidate":
            stay_days = random.randint(30, 240)
        elif segment == "critical":
            stay_days = random.randint(1, 40)
        else:
            stay_days = random.randint(10, 120)

        tentative_admission = now - timedelta(days=stay_days, hours=random.randint(0, 23))
        minimum_admission = base_time + timedelta(days=1)
        admission = max(tentative_admission, minimum_admission)
        return self._clamp_to_now(admission)

    @staticmethod
    def _advance_time(current: datetime, min_delta: timedelta, max_delta: timedelta) -> datetime:
        delta_seconds = random.randint(int(min_delta.total_seconds()), int(max_delta.total_seconds()))
        return current + timedelta(seconds=delta_seconds)

    @staticmethod
    def _clamp_to_now(candidate: datetime) -> datetime:
        return min(candidate, now_utc())
