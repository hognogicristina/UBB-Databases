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


from app.service.patient.treatment_evaluator import PatientTreatmentEvaluator


class PatientPostDischargeSummaryService(PatientTreatmentEvaluator):
    @classmethod
    def _build_episode_window(
            cls,
            db,
            *,
            patient_id: int,
            discharge_date: datetime,
    ) -> datetime | None:
        return db.execute(
            select(PatientAdmissionHistory.created_at)
            .where(
                PatientAdmissionHistory.patient_id == patient_id,
                func.lower(PatientAdmissionHistory.type) == "admission",
                PatientAdmissionHistory.created_at <= discharge_date,
            )
            .order_by(PatientAdmissionHistory.created_at.desc(), PatientAdmissionHistory.id.desc())
            .limit(1)
        ).scalar_one_or_none()
    @classmethod
    def _is_within_episode(
            cls,
            timestamp: datetime | None,
            *,
            episode_start: datetime | None,
            episode_end: datetime,
    ) -> bool:
        normalized_timestamp = cls._normalize_datetime_for_comparison(timestamp)
        normalized_end = cls._normalize_datetime_for_comparison(episode_end)
        normalized_start = cls._normalize_datetime_for_comparison(episode_start)

        if normalized_timestamp is None or normalized_end is None:
            return False
        if normalized_timestamp > normalized_end:
            return False
        if normalized_start is not None and normalized_timestamp < normalized_start:
            return False
        return True
    @classmethod
    def _build_post_discharge_clinical_summary(
            cls,
            *,
            diagnoses: list[str],
            conditions: list[str],
            total_alerts: int,
            most_problematic_vital: str,
            most_problematic_vital_abnormal_count: int,
            total_treatments: int,
            effective_treatments: int,
            improving_treatments: int,
            ineffective_treatments: int,
            final_treatment_outcome: str,
            final_patient_state: str,
            discharge_reason: str,
    ) -> str:
        monitored_targets = []
        if diagnoses:
            monitored_targets.append(", ".join(diagnoses[:3]))
        if conditions:
            monitored_targets.append(", ".join(conditions[:3]))
        if monitored_targets:
            intro = f"The patient was monitored for {' and '.join(monitored_targets)}."
        else:
            intro = "The patient was monitored for clinical instability during admission."

        if total_alerts > 0 and most_problematic_vital != "none":
            alert_sentence = (
                f"During admission, {cls._format_vital_label(most_problematic_vital)} produced the highest alert burden "
                f"({most_problematic_vital_abnormal_count} high or critical alerts)."
            )
        elif total_alerts > 0:
            alert_sentence = f"During admission, {total_alerts} alert events were recorded."
        else:
            alert_sentence = "No alert events were recorded during the tracked admission window."

        if total_treatments > 0:
            treatment_sentence = (
                f"{total_treatments} treatment actions were recorded "
                f"(Effective: {effective_treatments}, Improving: {improving_treatments}, Ineffective: {ineffective_treatments})."
            )
        else:
            treatment_sentence = "No treatment actions were recorded in the tracked admission window."

        if final_treatment_outcome == "Effective":
            outcome_sentence = (
                "The final treatment outcome was Effective, and discharge was aligned with stabilized monitored trends."
            )
        elif final_treatment_outcome == "Improving":
            outcome_sentence = (
                "The final treatment outcome was Improving, indicating partial recovery without full stabilization criteria."
            )
        elif final_treatment_outcome == "Ineffective":
            outcome_sentence = (
                "The final treatment outcome was Ineffective, with persistent instability requiring cautious follow-up."
            )
        else:
            outcome_sentence = "The final treatment outcome was not available from recorded treatment actions."

        discharge_sentence = f"Discharge reason: {discharge_reason}."
        final_state_sentence = f"Final clinical state: {final_patient_state}"

        return " ".join([intro, alert_sentence, treatment_sentence, outcome_sentence, discharge_sentence, final_state_sentence]).strip()
    @classmethod
    def _build_post_discharge_readmission_notes(
            cls,
            *,
            most_problematic_vital: str,
            most_problematic_vital_abnormal_count: int,
            unresolved_abnormal_vitals: list[str],
            final_treatment_outcome: str,
    ) -> str:
        if most_problematic_vital == "none":
            notes = "If readmitted, repeat baseline vital assessment and monitor for recurrent instability."
        else:
            notes = (
                f"If readmitted, monitor {cls._format_vital_label(most_problematic_vital)} closely because it generated "
                f"{most_problematic_vital_abnormal_count} high or critical alerts during the previous admission."
            )

        if unresolved_abnormal_vitals:
            unresolved_text = ", ".join(cls._format_vital_label(item) for item in unresolved_abnormal_vitals)
            notes = f"{notes} Unresolved abnormal alerts at discharge involved: {unresolved_text}."

        if final_treatment_outcome in {"Improving", "Ineffective"}:
            notes = f"{notes} Reassess treatment response early because the last recorded outcome was {final_treatment_outcome}."

        return notes
    @classmethod
    def _serialize_post_discharge_summary_row(cls, summary: PatientDischargeSummary) -> dict[str, Any]:
        return {
            "status": "ready",
            "patient_id": int(summary.patient_id),
            "discharge_date": summary.discharge_date,
            "discharge_reason": cls._safe_summary_text(summary.discharge_reason, "Not recorded."),
            "alert_metrics": {
                "total": int(summary.total_alerts or 0),
                "critical": int(summary.critical_alerts or 0),
                "high": int(summary.high_alerts or 0),
                "normal": int(summary.normal_alerts or 0),
                "normalized": int(summary.normalized_alerts or 0),
            },
            "treatment_metrics": {
                "total": int(summary.total_treatments or 0),
                "effective": int(summary.effective_treatments or 0),
                "improving": int(summary.improving_treatments or 0),
                "ineffective": int(summary.ineffective_treatments or 0),
            },
            "most_problematic_vital": cls._safe_summary_text(summary.most_problematic_vital, "none"),
            "final_treatment_outcome": cls._safe_summary_text(summary.final_treatment_outcome, "Not available"),
            "final_patient_state": cls._safe_summary_text(summary.final_patient_state, "No clinical state available."),
            "clinical_summary": cls._safe_summary_text(summary.clinical_summary, "No clinical summary available."),
            "readmission_notes": cls._safe_summary_text(summary.readmission_notes, "No readmission notes available."),
            "generated_at": summary.generated_at,
            "updated_at": summary.updated_at,
        }
    @classmethod
    def _build_post_discharge_summary_payload(cls, db, patient: Patient) -> dict[str, Any] | None:
        discharge_date = cls._normalize_datetime_for_comparison(patient.discharge_date)
        if discharge_date is None:
            return None

        episode_start = cls._build_episode_window(
            db,
            patient_id=patient.id,
            discharge_date=discharge_date,
        )

        alert_rows = db.execute(
            select(Alert)
            .where(Alert.patient_id == patient.id)
            .order_by(Alert.created_at.asc(), Alert.id.asc())
        ).scalars().all()
        relevant_alerts = [
            alert for alert in alert_rows
            if cls._is_within_episode(
                alert.created_at,
                episode_start=episode_start,
                episode_end=discharge_date,
            )
        ]

        vital_rows = db.execute(
            select(Vital)
            .where(Vital.patient_id == patient.id)
            .order_by(Vital.recorded_at.asc(), Vital.id.asc())
        ).scalars().all()
        relevant_vitals = [
            vital for vital in vital_rows
            if cls._is_within_episode(
                vital.recorded_at,
                episode_start=episode_start,
                episode_end=discharge_date,
            )
        ]

        medication_rows = db.execute(
            select(PatientMedication)
            .where(PatientMedication.patient_id == patient.id)
            .order_by(PatientMedication.created_at.asc(), PatientMedication.id.asc())
        ).scalars().all()
        relevant_medications = []
        for medication in medication_rows:
            created_in_window = cls._is_within_episode(
                medication.created_at,
                episode_start=episode_start,
                episode_end=discharge_date,
            )
            updated_in_window = cls._is_within_episode(
                medication.updated_at,
                episode_start=episode_start,
                episode_end=discharge_date,
            )
            if created_in_window or updated_in_window:
                relevant_medications.append(medication)

        treatment_actions = cls._build_treatment_actions(relevant_medications)
        treatment_actions = [
            action for action in treatment_actions
            if cls._is_within_episode(
                action.get("timestamp"),
                episode_start=episode_start,
                episode_end=discharge_date,
            )
        ]

        outcomes: list[str] = []
        for action_index in range(len(treatment_actions)):
            evaluation = cls._evaluate_treatment_action(
                patient=patient,
                action_index=action_index,
                treatment_actions=treatment_actions,
                sequence_vitals=relevant_vitals,
                sequence_alerts=relevant_alerts,
            )
            outcomes.append(str(evaluation.get("outcome") or "Ineffective"))

        total_treatments = len(treatment_actions)
        effective_treatments = sum(1 for outcome in outcomes if outcome == "Effective")
        improving_treatments = sum(1 for outcome in outcomes if outcome == "Improving")
        ineffective_treatments = sum(1 for outcome in outcomes if outcome == "Ineffective")
        final_treatment_outcome = outcomes[-1] if outcomes else "Not available"

        abnormal_counts_by_vital = {
            "heart_rate": 0,
            "oxygen_saturation": 0,
            "temperature": 0,
        }
        total_counts_by_vital = {
            "heart_rate": 0,
            "oxygen_saturation": 0,
            "temperature": 0,
        }
        critical_alerts = 0
        high_alerts = 0
        normal_alerts = 0
        normalized_alerts = 0

        for alert in relevant_alerts:
            severity = str(alert.severity or "").strip().lower()
            if severity == "critical":
                critical_alerts += 1
            elif severity == "high":
                high_alerts += 1
            else:
                normal_alerts += 1

            canonical_type = normalize_alert_type(alert.alert_type, alert.severity)
            alert_state = cls._classify_alert_state(canonical_type)
            if alert_state == "normalized":
                normalized_alerts += 1

            vital_key = vital_for_alert_type(canonical_type)
            mapped_vital_key = "oxygen_saturation" if vital_key == "oxygen" else vital_key
            if mapped_vital_key in total_counts_by_vital:
                total_counts_by_vital[mapped_vital_key] += 1
                if alert_state == "abnormal":
                    abnormal_counts_by_vital[mapped_vital_key] += 1

        total_alerts = len(relevant_alerts)
        most_problematic_vital = cls._pick_most_problematic_vital(abnormal_counts_by_vital, total_counts_by_vital)
        most_problematic_vital_abnormal_count = int(abnormal_counts_by_vital.get(most_problematic_vital, 0))

        final_alert_state = cls._get_latest_vital_specific_alert_state(
            sequence_alerts=relevant_alerts,
            window_end=discharge_date,
        )
        unresolved_abnormal_vitals = sorted(
            [
                key
                for key in ("heart_rate", "oxygen_saturation", "temperature")
                if str((final_alert_state.get(key) or {}).get("latest_state") or "").strip().lower() == "abnormal"
            ]
        )

        diagnosis_rows = db.execute(
            select(PatientDiagnosis)
            .where(PatientDiagnosis.patient_id == patient.id)
            .order_by(PatientDiagnosis.updated_at.desc(), PatientDiagnosis.id.desc())
        ).scalars().all()
        relevant_diagnoses = [
            diagnosis for diagnosis in diagnosis_rows
            if cls._is_within_episode(
                diagnosis.created_at,
                episode_start=episode_start,
                episode_end=discharge_date,
            )
        ]

        condition_rows = db.execute(
            select(PatientCondition, PatientConditionAssignment)
            .join(PatientConditionAssignment, PatientConditionAssignment.condition_id == PatientCondition.id)
            .where(PatientConditionAssignment.patient_id == patient.id)
            .order_by(PatientConditionAssignment.updated_at.desc(), PatientCondition.id.asc())
        ).all()
        relevant_conditions = [
            (condition, assignment)
            for condition, assignment in condition_rows
            if cls._is_within_episode(
                assignment.created_at,
                episode_start=episode_start,
                episode_end=discharge_date,
            )
        ]

        diagnosis_statuses = [
            f"{cls._safe_summary_text(item.diagnosis, 'Diagnosis')} ({cls._safe_summary_text(item.status, 'unknown')})"
            for item in relevant_diagnoses
        ]
        condition_statuses = [
            f"{cls._safe_summary_text(condition.name, 'Condition')} ({cls._safe_summary_text(assignment.status, 'unknown')})"
            for condition, assignment in relevant_conditions
        ]

        latest_vital = relevant_vitals[-1] if relevant_vitals else None
        final_vital_state_text = cls._build_final_vital_state_text(latest_vital)
        discharge_reason = cls._safe_summary_text(patient.discharge_reason, "Not recorded.")

        if unresolved_abnormal_vitals:
            unresolved_text = ", ".join(cls._format_vital_label(item) for item in unresolved_abnormal_vitals)
            final_patient_state = f"Unresolved abnormal alerts at discharge: {unresolved_text}. {final_vital_state_text}"
        elif final_treatment_outcome == "Effective":
            final_patient_state = f"Vitals and alert trends were stable at discharge. {final_vital_state_text}"
        elif final_treatment_outcome == "Improving":
            final_patient_state = f"Partial stabilization was observed at discharge. {final_vital_state_text}"
        elif final_treatment_outcome == "Ineffective":
            final_patient_state = f"Persistent instability remained at discharge. {final_vital_state_text}"
        else:
            final_patient_state = f"No conclusive treatment outcome was available. {final_vital_state_text}"

        clinical_summary = cls._build_post_discharge_clinical_summary(
            diagnoses=diagnosis_statuses,
            conditions=condition_statuses,
            total_alerts=total_alerts,
            most_problematic_vital=most_problematic_vital,
            most_problematic_vital_abnormal_count=most_problematic_vital_abnormal_count,
            total_treatments=total_treatments,
            effective_treatments=effective_treatments,
            improving_treatments=improving_treatments,
            ineffective_treatments=ineffective_treatments,
            final_treatment_outcome=final_treatment_outcome,
            final_patient_state=final_patient_state,
            discharge_reason=discharge_reason,
        )
        readmission_notes = cls._build_post_discharge_readmission_notes(
            most_problematic_vital=most_problematic_vital,
            most_problematic_vital_abnormal_count=most_problematic_vital_abnormal_count,
            unresolved_abnormal_vitals=unresolved_abnormal_vitals,
            final_treatment_outcome=final_treatment_outcome,
        )

        return {
            "patient_id": patient.id,
            "discharge_date": discharge_date,
            "discharge_reason": discharge_reason,
            "total_alerts": total_alerts,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "normal_alerts": normal_alerts,
            "normalized_alerts": normalized_alerts,
            "total_treatments": total_treatments,
            "effective_treatments": effective_treatments,
            "improving_treatments": improving_treatments,
            "ineffective_treatments": ineffective_treatments,
            "most_problematic_vital": most_problematic_vital,
            "final_treatment_outcome": final_treatment_outcome,
            "final_patient_state": final_patient_state,
            "clinical_summary": clinical_summary,
            "readmission_notes": readmission_notes,
        }
    @classmethod
    def generate_post_discharge_summaries(cls, db) -> dict[str, int]:
        discharged_patients = db.execute(
            select(Patient)
            .where(Patient.is_discharged.is_(True), Patient.discharge_date.is_not(None))
            .order_by(Patient.id.asc())
        ).scalars().all()

        generated_count = 0
        updated_count = 0
        pending_count = 0
        now = now_utc()

        for patient in discharged_patients:
            payload = cls._build_post_discharge_summary_payload(db, patient)
            if payload is None:
                pending_count += 1
                continue

            summary_row = db.execute(
                select(PatientDischargeSummary)
                .where(
                    PatientDischargeSummary.patient_id == patient.id,
                    PatientDischargeSummary.discharge_date == payload["discharge_date"],
                )
                .limit(1)
            ).scalar_one_or_none()

            if summary_row is None:
                summary_row = PatientDischargeSummary(
                    patient_id=patient.id,
                    discharge_date=payload["discharge_date"],
                    generated_at=now,
                )
                db.add(summary_row)
                generated_count += 1
            else:
                updated_count += 1

            summary_row.discharge_reason = payload["discharge_reason"]
            summary_row.total_alerts = payload["total_alerts"]
            summary_row.critical_alerts = payload["critical_alerts"]
            summary_row.high_alerts = payload["high_alerts"]
            summary_row.normal_alerts = payload["normal_alerts"]
            summary_row.normalized_alerts = payload["normalized_alerts"]
            summary_row.total_treatments = payload["total_treatments"]
            summary_row.effective_treatments = payload["effective_treatments"]
            summary_row.improving_treatments = payload["improving_treatments"]
            summary_row.ineffective_treatments = payload["ineffective_treatments"]
            summary_row.most_problematic_vital = payload["most_problematic_vital"]
            summary_row.final_treatment_outcome = payload["final_treatment_outcome"]
            summary_row.final_patient_state = payload["final_patient_state"]
            summary_row.clinical_summary = payload["clinical_summary"]
            summary_row.readmission_notes = payload["readmission_notes"]
            summary_row.updated_at = now

        return {
            "generated": generated_count,
            "updated": updated_count,
            "pending": pending_count,
        }
    def get_patient_post_discharge_summary(self, patient_id: int) -> dict[str, Any]:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)
            latest_summary = db.execute(
                select(PatientDischargeSummary)
                .where(PatientDischargeSummary.patient_id == patient_id)
                .order_by(PatientDischargeSummary.discharge_date.desc(), PatientDischargeSummary.id.desc())
                .limit(1)
            ).scalar_one_or_none()

            current_episode_summary = None
            if patient.is_discharged and patient.discharge_date is not None:
                current_episode_summary = db.execute(
                    select(PatientDischargeSummary)
                    .where(
                        PatientDischargeSummary.patient_id == patient_id,
                        PatientDischargeSummary.discharge_date == patient.discharge_date,
                    )
                    .limit(1)
                ).scalar_one_or_none()

            if current_episode_summary is not None:
                return self._serialize_post_discharge_summary_row(current_episode_summary)

            if patient.is_discharged:
                return {
                    "status": "pending",
                    "patient_id": int(patient.id),
                    "discharge_date": patient.discharge_date,
                    "discharge_reason": self._safe_summary_text(patient.discharge_reason, "Not recorded."),
                    "alert_metrics": None,
                    "treatment_metrics": None,
                    "most_problematic_vital": None,
                    "final_treatment_outcome": None,
                    "final_patient_state": None,
                    "clinical_summary": None,
                    "readmission_notes": None,
                    "generated_at": None,
                    "updated_at": None,
                }

            if latest_summary is not None:
                return self._serialize_post_discharge_summary_row(latest_summary)

            return {
                "status": "not_available",
                "patient_id": int(patient.id),
                "discharge_date": None,
                "discharge_reason": None,
                "alert_metrics": None,
                "treatment_metrics": None,
                "most_problematic_vital": None,
                "final_treatment_outcome": None,
                "final_patient_state": None,
                "clinical_summary": None,
                "readmission_notes": None,
                "generated_at": None,
                "updated_at": None,
            }
