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


from app.service.patient.alert_state_service import PatientAlertStateService


class PatientTreatmentEvaluator(PatientAlertStateService):
    @classmethod
    def _stable_vital_count(cls, vital: Vital | None) -> int:
        if vital is None:
            return 0
        stable_flags = [
            vital.heart_rate <= cls.HEART_RATE_STABLE_MAX,
            vital.oxygen_saturation >= cls.OXYGEN_STABLE_MIN,
            vital.temperature <= cls.TEMPERATURE_STABLE_MAX,
        ]
        return sum(1 for flag in stable_flags if flag)
    @classmethod
    def _build_treatment_actions(cls, medications: list[PatientMedication]) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        for medication in medications:
            created_at = cls._normalize_datetime_for_comparison(medication.created_at)
            updated_at = cls._normalize_datetime_for_comparison(medication.updated_at)
            actions.append(
                {
                    "action": "add",
                    "timestamp": created_at,
                    "medication": medication,
                }
            )
            if updated_at is not None and created_at is not None and updated_at > created_at:
                actions.append(
                    {
                        "action": "modify",
                        "timestamp": updated_at,
                        "medication": medication,
                    }
                )

        actions.sort(
            key=lambda item: (
                item["timestamp"],
                item["medication"].id,
                0 if item["action"] == "add" else 1,
            )
        )
        return actions

    @classmethod
    def build_treatment_actions(cls, medications: list[PatientMedication]) -> list[dict[str, Any]]:
        return cls._build_treatment_actions(medications)
    @classmethod
    def _build_treatment_evaluation_window(
            cls,
            *,
            patient: Patient,
            action_index: int,
            treatment_actions: list[dict[str, Any]],
            sequence_vitals: list[Vital],
            sequence_alerts: list[Alert],
    ) -> tuple[datetime, datetime]:
        action_time = cls._normalize_datetime_for_comparison(treatment_actions[action_index]["timestamp"])
        if action_time is None:
            fallback_now = now_utc()
            return fallback_now, fallback_now
        is_final = action_index == len(treatment_actions) - 1
        if not is_final:
            next_action_time = cls._normalize_datetime_for_comparison(treatment_actions[action_index + 1]["timestamp"])
            if next_action_time is None:
                return action_time, action_time
            return action_time, next_action_time

        if patient.discharge_date is not None:
            discharge_time = cls._normalize_datetime_for_comparison(patient.discharge_date)
            if discharge_time is not None:
                return action_time, discharge_time

        latest_vital_time = cls._normalize_datetime_for_comparison(sequence_vitals[-1].recorded_at) if sequence_vitals else None
        latest_alert_time = cls._normalize_datetime_for_comparison(sequence_alerts[-1].created_at) if sequence_alerts else None
        candidates = cls._normalize_datetime_candidates([latest_vital_time, latest_alert_time, action_time])
        if not candidates:
            return action_time, action_time
        return action_time, max(candidates)
    @classmethod
    def _get_latest_vital_state_for_window(
            cls,
            *,
            sequence_vitals: list[Vital],
            window_start: datetime,
            window_end: datetime,
    ) -> tuple[Vital | None, str]:
        normalized_window_start = cls._normalize_datetime_for_comparison(window_start)
        normalized_window_end = cls._normalize_datetime_for_comparison(window_end)
        if normalized_window_start is None or normalized_window_end is None:
            return None, "no_vital_available"

        in_window = [
            vital for vital in sequence_vitals
            if (
                (normalized_vital_time := cls._normalize_datetime_for_comparison(vital.recorded_at)) is not None
                and normalized_window_start <= normalized_vital_time <= normalized_window_end
            )
        ]
        if in_window:
            return in_window[-1], "latest_vital_in_window"

        before_end = [
            vital for vital in sequence_vitals
            if (
                (normalized_vital_time := cls._normalize_datetime_for_comparison(vital.recorded_at)) is not None
                and normalized_vital_time <= normalized_window_end
            )
        ]
        if before_end:
            return before_end[-1], "latest_vital_before_window_end"
        return None, "no_vital_available"
    @classmethod
    def _get_latest_vital_before_timestamp(
            cls,
            *,
            sequence_vitals: list[Vital],
            timestamp: datetime | None,
    ) -> Vital | None:
        normalized_timestamp = cls._normalize_datetime_for_comparison(timestamp)
        if normalized_timestamp is None:
            return None

        for vital in reversed(sequence_vitals):
            vital_time = cls._normalize_datetime_for_comparison(vital.recorded_at)
            if vital_time is not None and vital_time < normalized_timestamp:
                return vital
        return None
    @classmethod
    def _get_vital_trend_improvements(
            cls,
            *,
            previous_vital: Vital | None,
            current_vital: Vital | None,
    ) -> list[str]:
        if previous_vital is None or current_vital is None:
            return []

        improvements: set[str] = set()

        if (
                previous_vital.heart_rate > cls.HEART_RATE_STABLE_MAX
                and (
                        current_vital.heart_rate <= cls.HEART_RATE_STABLE_MAX
                        or current_vital.heart_rate <= (previous_vital.heart_rate - 4)
                )
        ):
            improvements.add("heart_rate")

        if (
                previous_vital.oxygen_saturation < cls.OXYGEN_STABLE_MIN
                and (
                        current_vital.oxygen_saturation >= cls.OXYGEN_STABLE_MIN
                        or current_vital.oxygen_saturation >= (previous_vital.oxygen_saturation + 1)
                )
        ):
            improvements.add("oxygen_saturation")

        if (
                previous_vital.temperature > cls.TEMPERATURE_STABLE_MAX
                and (
                        current_vital.temperature <= cls.TEMPERATURE_STABLE_MAX
                        or current_vital.temperature <= (previous_vital.temperature - 0.2)
                )
        ):
            improvements.add("temperature")

        return sorted(improvements)
    @staticmethod
    def _is_treatment_escalation_due_to_worsening(
            *,
            next_action: dict[str, Any] | None,
    ) -> bool:
        if next_action is None:
            return False

        next_medication = next_action["medication"]
        notes = " ".join(
            [
                str(next_medication.notes or ""),
                str(next_medication.last_updated_note or ""),
            ]
        ).strip().lower()
        if not notes:
            return False

        escalation_markers = [
            "persistent alert",
            "treatment not working",
            "worse",
            "worsen",
            "ineffective",
            "dose",
            "frequency adjusted",
            "escalat",
        ]
        return any(marker in notes for marker in escalation_markers)
    @classmethod
    def _derive_treatment_outcome_from_window(
            cls,
            *,
            action_index: int,
            total_actions: int,
            pre_treatment_vital: Vital | None,
            evaluated_vital: Vital | None,
            full_alert_state: dict[str, dict[str, Any]],
            post_treatment_alert_state: dict[str, dict[str, Any]],
            sequence_alerts: list[Alert],
            treatment_timestamp: datetime | None,
            window_end: datetime,
            unresolved_after_treatment_vitals: list[str],
            next_action: dict[str, Any] | None,
    ) -> tuple[str, str, dict[str, Any]]:
        vital_rules = {
            "heart_rate": {
                "label": "heart_rate",
                "threshold_text": f"<= {cls.HEART_RATE_STABLE_MAX}",
                "is_stable": lambda value: value <= cls.HEART_RATE_STABLE_MAX,
            },
            "oxygen_saturation": {
                "label": "oxygen_saturation",
                "threshold_text": f">= {cls.OXYGEN_STABLE_MIN}",
                "is_stable": lambda value: value >= cls.OXYGEN_STABLE_MIN,
            },
            "temperature": {
                "label": "temperature",
                "threshold_text": f"<= {cls.TEMPERATURE_STABLE_MAX}",
                "is_stable": lambda value: value <= cls.TEMPERATURE_STABLE_MAX,
            },
        }

        stable_reasons: list[str] = []
        vital_unstable_signals: list[str] = []
        vital_evidence: dict[str, Any] = {}
        all_latest_vitals_stable = evaluated_vital is not None

        for key, rule in vital_rules.items():
            value = getattr(evaluated_vital, key) if evaluated_vital is not None else None
            vital_alert_state = full_alert_state.get(key, {})
            latest_state = str(vital_alert_state.get("latest_state") or "none")
            latest_alert = vital_alert_state.get("latest")
            latest_alert_payload = (
                {
                    "id": latest_alert.id,
                    "alert_type": normalize_alert_type(latest_alert.alert_type, latest_alert.severity),
                    "severity": latest_alert.severity,
                    "message": latest_alert.message,
                    "created_at": latest_alert.created_at,
                } if latest_alert is not None else None
            )

            threshold_stable = None
            if value is not None:
                threshold_stable = bool(rule["is_stable"](value))
                if threshold_stable:
                    stable_reasons.append(f"{rule['label']}={value} satisfies {rule['threshold_text']}")
                else:
                    all_latest_vitals_stable = False
                    vital_unstable_signals.append(f"{rule['label']}={value} violates {rule['threshold_text']}")
            else:
                all_latest_vitals_stable = False
                vital_unstable_signals.append(f"{rule['label']} has no latest vital value for evaluation")

            vital_evidence[key] = {
                "value": value,
                "threshold": rule["threshold_text"],
                "threshold_stable": threshold_stable,
                "latest_alert_state": latest_state,
                "latest_alert": latest_alert_payload,
            }

        if treatment_timestamp is None:
            recovered_vitals: list[str] = []
            complete_recovery_snapshot = None
        else:
            recovered_vitals = cls._get_recovered_vitals_after_treatment(
                sequence_alerts=sequence_alerts,
                window_start=treatment_timestamp,
                window_end=window_end,
                post_treatment_alert_state=post_treatment_alert_state,
                full_alert_state=full_alert_state,
            )
            complete_recovery_snapshot = cls._find_complete_recovery_snapshot(
                sequence_alerts=sequence_alerts,
                window_start=treatment_timestamp,
                window_end=window_end,
            )

        unresolved_vitals = cls._get_unresolved_abnormal_vitals(
            full_alert_state=full_alert_state,
            unresolved_after_treatment_vitals=unresolved_after_treatment_vitals,
        )

        next_treatment_escalation = cls._is_treatment_escalation_due_to_worsening(
            next_action=next_action,
        )
        latest_alerts = cls._build_latest_alert_debug_payload(full_alert_state)

        trend_improved_vitals = cls._get_vital_trend_improvements(
            previous_vital=pre_treatment_vital,
            current_vital=evaluated_vital,
        )
        recovery_signals_vitals = sorted(set(recovered_vitals) | set(trend_improved_vitals))
        stable_vital_count_before = cls._stable_vital_count(pre_treatment_vital)
        stable_vital_count_after = cls._stable_vital_count(evaluated_vital)
        stable_vital_count_gain = max(0, stable_vital_count_after - stable_vital_count_before)

        has_unresolved = bool(unresolved_vitals)
        has_recovery = bool(recovery_signals_vitals)
        has_unstable_values = not all_latest_vitals_stable

        unstable_signals: list[str] = [*vital_unstable_signals]
        if has_unresolved:
            unstable_signals.append(
                "Unresolved abnormal alerts remain for: "
                + ", ".join(cls._format_vital_label(item) for item in unresolved_vitals)
            )
        if has_unstable_values:
            unstable_signals.append(
                "Latest vital values are not fully stable (heart_rate, oxygen_saturation, temperature)."
            )
        if next_treatment_escalation and (has_unresolved or has_unstable_values):
            unstable_signals.append(
                "A follow-up treatment escalation indicates persistent or worsening clinical instability."
            )

        evidence = {
            "vitals": vital_evidence,
            "stable_signals": stable_reasons,
            "unstable_signals": unstable_signals,
            "recovered_vitals": recovered_vitals,
            "trend_improved_vitals": trend_improved_vitals,
            "recovery_signals_vitals": recovery_signals_vitals,
            "unresolved_vitals": unresolved_vitals,
            "has_unresolved_abnormal_alerts": has_unresolved,
            "next_treatment_escalation_detected": next_treatment_escalation,
            "complete_recovery_at": (
                complete_recovery_snapshot.get("recovered_at")
                if complete_recovery_snapshot is not None
                else None
            ),
            "action_index": action_index + 1,
            "total_actions": total_actions,
            "stable_vital_count_before": stable_vital_count_before,
            "stable_vital_count_after": stable_vital_count_after,
            "stable_vital_count_gain": stable_vital_count_gain,
            "latest_alerts": latest_alerts,
        }

        if all_latest_vitals_stable and not has_unresolved:
            if recovered_vitals:
                reason = (
                    "Treatment is effective because "
                    + ", ".join(cls._format_vital_label(item) for item in recovered_vitals)
                    + " normalized after treatment and no unresolved abnormal alerts remain."
                )
            else:
                reason = "Treatment is effective because latest vital values are stable and no unresolved abnormal alerts remain."
            return "Effective", reason, evidence

        if next_action is not None and complete_recovery_snapshot is not None:
            complete_recovered_vitals = list(complete_recovery_snapshot.get("recovered_vitals") or [])
            complete_recovered_labels = complete_recovered_vitals or recovered_vitals
            if complete_recovered_labels:
                reason = (
                    "Treatment was effective because "
                    + ", ".join(cls._format_vital_label(item) for item in complete_recovered_labels)
                    + " normalized after treatment before later alerts appeared."
                )
            else:
                reason = "Treatment was effective because abnormal alerts resolved before later alerts appeared."
            effective_evidence = {
                **evidence,
                "unstable_signals": [],
                "recovered_vitals": complete_recovered_vitals,
                "recovery_signals_vitals": sorted(set(recovery_signals_vitals) | set(complete_recovered_vitals)),
                "unresolved_vitals": [],
                "has_unresolved_abnormal_alerts": False,
                "latest_alerts": complete_recovery_snapshot.get("latest_alerts"),
            }
            return "Effective", reason, effective_evidence

        treatment_number = action_index + 1
        phase_bonus = 0
        if 4 <= treatment_number <= 7:
            phase_bonus = 1
        elif treatment_number >= 8:
            phase_bonus = 2

        improving_threshold = 3
        if 4 <= treatment_number <= 7:
            improving_threshold = 2
        elif treatment_number >= 8:
            improving_threshold = 1

        progression_score = 0
        if has_recovery:
            progression_score += 2
        if stable_vital_count_gain > 0:
            progression_score += 1
        if not has_unresolved:
            progression_score += 1
        if not has_unstable_values:
            progression_score += 1
        if next_treatment_escalation:
            progression_score -= 1
        if phase_bonus > 0 and (has_recovery or stable_vital_count_gain > 0):
            progression_score += phase_bonus

        if (
                (has_recovery and (has_unresolved or has_unstable_values or next_treatment_escalation))
                or progression_score >= improving_threshold
                or (
                    treatment_number >= 4
                    and not next_treatment_escalation
                    and stable_vital_count_after >= stable_vital_count_before
                    and (has_recovery or stable_vital_count_after >= 2)
                )
        ):
            recovery_labels = recovery_signals_vitals or recovered_vitals
            unresolved_phrase = (
                ", and "
                + ", ".join(cls._format_vital_label(item) for item in unresolved_vitals)
                + " remains unresolved"
                if unresolved_vitals
                else ""
            )
            if recovery_labels:
                reason = (
                    "Treatment is improving because "
                    + ", ".join(cls._format_vital_label(item) for item in recovery_labels)
                    + " shows recovery after treatment"
                    + unresolved_phrase
                    + "."
                )
            else:
                reason = (
                    "Treatment is improving because clinical stability indicators are increasing, "
                    "but the patient is not fully recovered yet."
                )
            return "Improving", reason, evidence

        reason = "Treatment is ineffective because abnormal states remain unresolved and no meaningful post-treatment recovery evidence is present."
        return "Ineffective", reason, evidence
    @classmethod
    def _derive_treatment_outcome_from_alert_recovery(
            cls,
            *,
            action_index: int,
            total_actions: int,
            pre_treatment_vital: Vital | None,
            evaluated_vital: Vital | None,
            full_alert_state: dict[str, dict[str, Any]],
            post_treatment_alert_state: dict[str, dict[str, Any]],
            sequence_alerts: list[Alert],
            treatment_timestamp: datetime | None,
            window_end: datetime,
            unresolved_after_treatment_vitals: list[str],
            next_action: dict[str, Any] | None,
    ) -> tuple[str, str, dict[str, Any]]:
        return cls._derive_treatment_outcome_from_window(
            action_index=action_index,
            total_actions=total_actions,
            pre_treatment_vital=pre_treatment_vital,
            evaluated_vital=evaluated_vital,
            full_alert_state=full_alert_state,
            post_treatment_alert_state=post_treatment_alert_state,
            sequence_alerts=sequence_alerts,
            treatment_timestamp=treatment_timestamp,
            window_end=window_end,
            unresolved_after_treatment_vitals=unresolved_after_treatment_vitals,
            next_action=next_action,
        )
    @classmethod
    def _evaluate_treatment_action(
            cls,
            *,
            patient: Patient,
            action_index: int,
            treatment_actions: list[dict[str, Any]],
            sequence_vitals: list[Vital],
            sequence_alerts: list[Alert],
    ) -> dict[str, Any]:
        current_action = treatment_actions[action_index]
        next_action = treatment_actions[action_index + 1] if action_index + 1 < len(treatment_actions) else None
        pre_treatment_vital = cls._get_latest_vital_before_timestamp(
            sequence_vitals=sequence_vitals,
            timestamp=current_action["timestamp"],
        )
        window_start, window_end = cls._build_treatment_evaluation_window(
            patient=patient,
            action_index=action_index,
            treatment_actions=treatment_actions,
            sequence_vitals=sequence_vitals,
            sequence_alerts=sequence_alerts,
        )
        evaluated_vital, evaluated_vital_source = cls._get_latest_vital_state_for_window(
            sequence_vitals=sequence_vitals,
            window_start=window_start,
            window_end=window_end,
        )
        vital_alert_state = cls._get_latest_vital_specific_alert_state(
            sequence_alerts=sequence_alerts,
            window_start=current_action["timestamp"],
            window_end=window_end,
        )
        _, unresolved_after_treatment_details = cls._has_unresolved_abnormal_alerts_after_in_sequence(
            sequence_alerts=sequence_alerts,
            after_timestamp=current_action["timestamp"],
            up_to_timestamp=window_end,
        )

        outcome, outcome_reason, outcome_evidence = cls._derive_treatment_outcome_from_alert_recovery(
            action_index=action_index,
            total_actions=len(treatment_actions),
            pre_treatment_vital=pre_treatment_vital,
            evaluated_vital=evaluated_vital,
            full_alert_state=cls._get_latest_vital_specific_alert_state(
                sequence_alerts=sequence_alerts,
                window_end=window_end,
            ),
            post_treatment_alert_state=vital_alert_state,
            sequence_alerts=sequence_alerts,
            treatment_timestamp=current_action["timestamp"],
            window_end=window_end,
            unresolved_after_treatment_vitals=unresolved_after_treatment_details.get("unresolved_vitals", []),
            next_action=next_action,
        )
        complete_recovery_at = (outcome_evidence or {}).get("complete_recovery_at")
        if outcome == "Effective" and complete_recovery_at is not None:
            recovery_vital, recovery_vital_source = cls._get_latest_vital_state_for_window(
                sequence_vitals=sequence_vitals,
                window_start=window_start,
                window_end=complete_recovery_at,
            )
            if recovery_vital is not None:
                evaluated_vital = recovery_vital
                evaluated_vital_source = f"{recovery_vital_source}_at_complete_recovery"

        evaluated_vital_payload = (
            {
                "heart_rate": evaluated_vital.heart_rate,
                "oxygen_saturation": evaluated_vital.oxygen_saturation,
                "temperature": evaluated_vital.temperature,
            } if evaluated_vital is not None else None
        )
        return {
            "outcome": outcome,
            "selected_vital_source": evaluated_vital_source,
            "selected_vital_timestamp": evaluated_vital.recorded_at if evaluated_vital is not None else None,
            "selected_vital": evaluated_vital_payload,
            "evaluation_start": window_start,
            "evaluation_end": window_end,
            "evaluated_vital_timestamp": evaluated_vital.recorded_at if evaluated_vital is not None else None,
            "evaluated_vital": evaluated_vital_payload,
            "outcome_reason": outcome_reason,
            "outcome_evidence": outcome_evidence,
            "recovered_vitals": list((outcome_evidence or {}).get("recovered_vitals") or []),
            "unresolved_vitals": list((outcome_evidence or {}).get("unresolved_vitals") or []),
            "latest_alerts": (outcome_evidence or {}).get("latest_alerts"),
        }

    @classmethod
    def evaluate_treatment_action(
            cls,
            *,
            patient: Patient,
            action_index: int,
            treatment_actions: list[dict[str, Any]],
            sequence_vitals: list[Vital],
            sequence_alerts: list[Alert],
    ) -> dict[str, Any]:
        return cls._evaluate_treatment_action(
            patient=patient,
            action_index=action_index,
            treatment_actions=treatment_actions,
            sequence_vitals=sequence_vitals,
            sequence_alerts=sequence_alerts,
        )
    @classmethod
    def _latest_treatment_action_outcome(cls, db, patient_id: int) -> dict | None:
        patient = db.get(Patient, patient_id)
        if patient is None:
            return None

        medications = db.execute(
            select(PatientMedication)
            .where(PatientMedication.patient_id == patient_id)
            .order_by(PatientMedication.created_at.asc(), PatientMedication.id.asc())
        ).scalars().all()
        if not medications:
            return None

        vitals = db.execute(
            select(Vital)
            .where(Vital.patient_id == patient_id)
            .order_by(Vital.recorded_at.asc(), Vital.id.asc())
        ).scalars().all()
        alerts = db.execute(
            select(Alert)
            .where(Alert.patient_id == patient_id)
            .order_by(Alert.created_at.asc(), Alert.id.asc())
        ).scalars().all()
        treatment_actions = cls._build_treatment_actions(medications)
        if not treatment_actions:
            return None

        latest_action = treatment_actions[-1]
        latest_index = len(treatment_actions) - 1
        evaluation = cls._evaluate_treatment_action(
            patient=patient,
            action_index=latest_index,
            treatment_actions=treatment_actions,
            sequence_vitals=vitals,
            sequence_alerts=alerts,
        )

        medication = latest_action["medication"]
        return {
            "medication_id": medication.id,
            "medication_name": medication.name,
            "action_type": latest_action["action"],
            "action_timestamp": latest_action["timestamp"],
            **evaluation,
        }

    @classmethod
    def get_latest_treatment_action_outcome(cls, db, patient_id: int) -> dict | None:
        return cls._latest_treatment_action_outcome(db, patient_id)
    @staticmethod
    def _build_treatment_reasoning_payload(
            *,
            medication: PatientMedication,
            alerts: list[Alert],
            diagnosis_labels: list[str],
            condition_labels: list[str],
    ) -> dict:
        medication_time = medication.created_at
        closest_alerts = sorted(
            alerts,
            key=lambda item: abs((item.created_at - medication_time).total_seconds()),
        )[:3]

        alert_labels = [f"{normalize_alert_type(item.alert_type, item.severity)}: {item.message}" for item in closest_alerts]

        if not alert_labels and alerts:
            recent_alerts = sorted(alerts, key=lambda item: item.created_at, reverse=True)[:3]
            alert_labels = [f"{normalize_alert_type(item.alert_type, item.severity)}: {item.message}" for item in recent_alerts]

        return {
            "alerts": alert_labels,
            "diagnoses": diagnosis_labels,
            "conditions": condition_labels,
        }
    def get_patient_treatment_analysis(self, patient_id: int) -> dict:
        with SessionLocal() as db:
            patient = get_patient_or_raise(db, patient_id)

            medications = db.execute(
                select(PatientMedication)
                .where(PatientMedication.patient_id == patient_id)
                .order_by(PatientMedication.created_at.asc(), PatientMedication.id.asc())
            ).scalars().all()

            diagnoses = db.execute(
                select(PatientDiagnosis)
                .where(PatientDiagnosis.patient_id == patient_id)
                .order_by(PatientDiagnosis.created_at.asc(), PatientDiagnosis.id.asc())
            ).scalars().all()

            condition_rows = db.execute(
                select(PatientCondition, PatientConditionAssignment)
                .join(PatientConditionAssignment, PatientConditionAssignment.condition_id == PatientCondition.id)
                .where(PatientConditionAssignment.patient_id == patient_id)
                .order_by(PatientConditionAssignment.created_at.asc(), PatientCondition.id.asc())
            ).all()

            alerts = db.execute(
                select(Alert)
                .where(Alert.patient_id == patient_id)
                .order_by(Alert.created_at.asc(), Alert.id.asc())
            ).scalars().all()
            vitals = db.execute(
                select(Vital)
                .where(Vital.patient_id == patient_id)
                .order_by(Vital.recorded_at.asc(), Vital.id.asc())
            ).scalars().all()
            diagnosis_labels = [entry.diagnosis for entry in diagnoses if entry.diagnosis]
            condition_labels = [
                f"{condition.name} ({assignment.status})"
                for condition, assignment in condition_rows
                if condition.name
            ]

            sequence_alerts = sorted(alerts, key=lambda item: (item.created_at, item.id))
            sequence_vitals = sorted(vitals, key=lambda item: (item.recorded_at, item.id))

            treatment_actions = self._build_treatment_actions(medications)

            medications_payload = []
            for action_index, action_entry in enumerate(treatment_actions):
                medication = action_entry["medication"]
                action_type = action_entry["action"]
                action_time = action_entry["timestamp"]
                index = action_index + 1
                doctor_name = None
                doctor = db.get(Doctor, medication.doctor_id)
                if doctor is not None:
                    doctor_name = f"{doctor.last_name} {doctor.first_name}".strip()
                evaluation = self._evaluate_treatment_action(
                    patient=patient,
                    action_index=action_index,
                    treatment_actions=treatment_actions,
                    sequence_vitals=sequence_vitals,
                    sequence_alerts=sequence_alerts,
                )

                previous_alert = next(
                    (
                        alert
                        for alert in reversed(sequence_alerts)
                        if (
                            (alert_time := self._normalize_datetime_for_comparison(alert.created_at)) is not None
                            and action_time is not None
                            and alert_time <= action_time
                        )
                    ),
                    None,
                )

                medications_payload.append(
                    {
                        "id": medication.id,
                        "action": action_type,
                        "name": medication.name,
                        "dosage": medication.dosage,
                        "frequency": medication.frequency,
                        "created_at": medication.created_at,
                        "prescribed_at": action_time,
                        "timestamp": action_time,
                        "updated_at": medication.updated_at,
                        "notes": medication.notes,
                        "last_updated_note": medication.last_updated_note,
                        "modified_by": doctor_name,
                        "treatment_index": index,
                        **evaluation,
                        "previous_alert": (
                            {
                                "alert_type": normalize_alert_type(previous_alert.alert_type, previous_alert.severity),
                                "severity": previous_alert.severity,
                                "message": previous_alert.message,
                                "created_at": previous_alert.created_at,
                            } if previous_alert is not None else None
                        ),
                        "next_alert": None,
                        "reasoning": self._build_treatment_reasoning_payload(
                            medication=medication,
                            alerts=alerts,
                            diagnosis_labels=diagnosis_labels,
                            condition_labels=condition_labels,
                        ),
                    }
                )

            diagnoses_payload = [
                {
                    "id": diagnosis.id,
                    "diagnosis": diagnosis.diagnosis,
                    "status": diagnosis.status,
                    "notes": diagnosis.notes,
                    "status_note": diagnosis.status_note,
                    "modified_by": (
                        f"{doctor.last_name} {doctor.first_name}".strip()
                        if (doctor := db.get(Doctor, diagnosis.doctor_id)) is not None
                        else None
                    ),
                    "created_at": diagnosis.created_at,
                }
                for diagnosis in diagnoses
            ]

            conditions_payload = [
                {
                    "id": condition.id,
                    "name": condition.name,
                    "status": assignment.status,
                    "notes": assignment.notes,
                    "modified_by": (
                        f"{doctor.last_name} {doctor.first_name}".strip()
                        if (doctor := db.get(Doctor, assignment.doctor_id)) is not None
                        else None
                    ),
                    "diagnosed_at": assignment.diagnosed_at,
                    "updated_at": assignment.updated_at,
                }
                for condition, assignment in condition_rows
            ]

            alerts_payload = []
            for alert in alerts:
                alert_type, value, unit, vitals = self._extract_alert_structured_fields(
                    alert.alert_type,
                    alert.message,
                    alert.severity,
                )
                alerts_payload.append(
                    {
                        "id": alert.id,
                        "alert_type": normalize_alert_type(alert.alert_type, alert.severity),
                        "type": alert_type,
                        "value": value,
                        "unit": unit,
                        "vitals": vitals,
                        "message": alert.message,
                        "severity": alert.severity,
                        "created_at": alert.created_at,
                    }
                )

            timeline_events = []
            for medication in medications:
                timeline_events.append(
                    {
                        "timestamp": medication.created_at,
                        "event_type": "medication",
                        "title": medication.name,
                        "details": f"{medication.dosage}, {medication.frequency}",
                        "related_medication_id": medication.id,
                    }
                )

            for alert in alerts:
                timeline_events.append(
                    {
                        "timestamp": alert.created_at,
                        "event_type": "alert",
                        "title": normalize_alert_type(alert.alert_type, alert.severity),
                        "details": alert.message,
                        "related_medication_id": None,
                    }
                )

            if medications:
                first_medication = medications[0].created_at - timedelta(days=30)
                last_medication = medications[-1].created_at + timedelta(days=30)
                timeline_events = [
                    event
                    for event in timeline_events
                    if first_medication <= event["timestamp"] <= last_medication or event["event_type"] == "medication"
                ]

            timeline_events.sort(key=lambda event: (event["timestamp"], event["event_type"]))

            return {
                "medications": medications_payload,
                "diagnoses": diagnoses_payload,
                "conditions": conditions_payload,
                "alerts": alerts_payload,
                "timeline": timeline_events,
            }
