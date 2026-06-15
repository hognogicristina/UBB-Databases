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


class PatientDischargeService(PatientTreatmentEvaluator):
    @classmethod
    def can_discharge_patient_as_recovered(
            cls,
            db,
            patient_id: int,
            final_treatment: dict[str, Any] | None,
            *,
            discharge_timestamp: datetime | None = None,
            required_stability_window_seconds: int = 0,
            stability_started_at: datetime | None = None,
            min_treatment_actions_required: int | None = None,
    ) -> tuple[bool, str, dict[str, Any]]:
        candidate_discharge_time = discharge_timestamp or now_utc()
        required_actions = (
            cls.MIN_TREATMENT_ACTIONS_BEFORE_RECOVERY_DISCHARGE
            if min_treatment_actions_required is None
            else max(0, int(min_treatment_actions_required))
        )
        treatment_outcome = str((final_treatment or {}).get("outcome") or "").strip()
        final_treatment_timestamp = (final_treatment or {}).get("action_timestamp")
        latest_vital = cls.get_latest_vital_state(
            db,
            patient_id,
            up_to_timestamp=candidate_discharge_time,
        )
        full_alert_state = cls.get_latest_vital_alert_state(
            db,
            patient_id,
            up_to_timestamp=candidate_discharge_time,
        )
        post_treatment_alert_state = full_alert_state
        if final_treatment_timestamp is not None:
            sequence_alerts = db.execute(
                select(Alert)
                .where(Alert.patient_id == patient_id)
                .order_by(Alert.created_at.asc(), Alert.id.asc())
            ).scalars().all()
            post_treatment_alert_state = cls._get_latest_vital_specific_alert_state(
                sequence_alerts=sequence_alerts,
                window_start=final_treatment_timestamp,
                window_end=candidate_discharge_time,
            )

        latest_alert_debug: dict[str, dict[str, Any] | None] = {}
        latest_abnormal_vitals: list[str] = []
        for vital_key, mapped_key in (
                ("heart_rate", "heart_rate"),
                ("oxygen_saturation", "oxygen_saturation"),
                ("temperature", "temperature"),
        ):
            latest_overall_bucket = full_alert_state.get(mapped_key) or {}
            latest_post_treatment_bucket = post_treatment_alert_state.get(mapped_key) or {}
            alert = latest_post_treatment_bucket.get("latest")
            state_source_bucket = latest_post_treatment_bucket
            if alert is None:
                alert = latest_overall_bucket.get("latest")
                state_source_bucket = latest_overall_bucket
            if alert is None:
                latest_alert_debug[vital_key] = None
                continue
            canonical_type = normalize_alert_type(alert.alert_type, alert.severity)
            inferred_state = cls._classify_alert_state(canonical_type)
            latest_state = state_source_bucket.get("latest_state")
            if latest_state not in {"abnormal", "normalized"}:
                latest_state = inferred_state
            if latest_state == "abnormal":
                latest_abnormal_vitals.append(vital_key)
            _, value, _, _ = cls._extract_alert_structured_fields(
                alert.alert_type,
                alert.message,
                alert.severity,
            )
            latest_alert_debug[vital_key] = {
                "type": canonical_type,
                "severity": alert.severity,
                "timestamp": alert.created_at,
                "value": value,
                "message": alert.message,
                "state": latest_state or "none",
            }

        debug_payload = {
            "patient_id": patient_id,
            "final_treatment_id": (final_treatment or {}).get("medication_id"),
            "final_treatment_timestamp": final_treatment_timestamp,
            "final_treatment_outcome": treatment_outcome,
            "evaluated_vital_timestamp": (final_treatment or {}).get("evaluated_vital_timestamp"),
            "evaluated_vital": (final_treatment or {}).get("evaluated_vital"),
            "latest_vital_timestamp": latest_vital.recorded_at if latest_vital is not None else None,
            "latest_vital": {
                "heart_rate": latest_vital.heart_rate if latest_vital is not None else None,
                "oxygen_saturation": latest_vital.oxygen_saturation if latest_vital is not None else None,
                "temperature": latest_vital.temperature if latest_vital is not None else None,
            },
            "latest_hr_vital_value": latest_vital.heart_rate if latest_vital is not None else None,
            "latest_hr_vital_timestamp": latest_vital.recorded_at if latest_vital is not None else None,
            "latest_oxygen_vital_value": latest_vital.oxygen_saturation if latest_vital is not None else None,
            "latest_oxygen_vital_timestamp": latest_vital.recorded_at if latest_vital is not None else None,
            "latest_temperature_vital_value": latest_vital.temperature if latest_vital is not None else None,
            "latest_temperature_vital_timestamp": latest_vital.recorded_at if latest_vital is not None else None,
            "discharge_timestamp_candidate": candidate_discharge_time,
            "latest_alerts": latest_alert_debug,
        }

        if treatment_outcome != "Effective":
            debug_payload["reason"] = "Blocked recovered discharge because final treatment outcome is not Effective."
            return False, "final_treatment_outcome_not_effective", debug_payload
        if final_treatment_timestamp is None:
            debug_payload["reason"] = "Blocked recovered discharge because final treatment timestamp is missing."
            return False, "final_treatment_timestamp_missing", debug_payload
        if latest_vital is None:
            debug_payload["reason"] = "Blocked recovered discharge because no latest vital snapshot is available."
            return False, "latest_vital_missing", debug_payload

        treatment_actions_count = 0
        if required_actions > 0:
            medications = db.execute(
                select(PatientMedication)
                .where(PatientMedication.patient_id == patient_id)
                .order_by(PatientMedication.created_at.asc(), PatientMedication.id.asc())
            ).scalars().all()
            treatment_actions_count = len(cls._build_treatment_actions(medications))
            debug_payload["treatment_actions_count"] = treatment_actions_count
            debug_payload["min_treatment_actions_required"] = required_actions
            if treatment_actions_count < required_actions:
                debug_payload["reason"] = (
                    "Blocked recovered discharge because treatment history is too short: "
                    f"{treatment_actions_count} action(s) recorded, minimum required is {required_actions}."
                )
                return False, "minimum_treatment_actions_not_met", debug_payload

        if latest_vital.heart_rate > cls.HEART_RATE_STABLE_MAX:
            debug_payload["reason"] = (
                f"Blocked recovered discharge because latest heart rate vital is {latest_vital.heart_rate} "
                f"(>{cls.HEART_RATE_STABLE_MAX})."
            )
            return False, "latest_heart_rate_unstable", debug_payload
        if latest_vital.oxygen_saturation < cls.OXYGEN_STABLE_MIN:
            debug_payload["reason"] = (
                f"Blocked recovered discharge because latest oxygen vital is {latest_vital.oxygen_saturation} "
                f"(<{cls.OXYGEN_STABLE_MIN})."
            )
            return False, "latest_oxygen_unstable", debug_payload
        if latest_vital.temperature > cls.TEMPERATURE_STABLE_MAX:
            debug_payload["reason"] = (
                f"Blocked recovered discharge because latest temperature vital is {latest_vital.temperature} "
                f"(>{cls.TEMPERATURE_STABLE_MAX})."
            )
            return False, "latest_temperature_unstable", debug_payload

        unresolved_after_treatment, unresolved_details = cls.has_unresolved_abnormal_alerts_after(
            db,
            patient_id,
            final_treatment_timestamp,
            up_to_timestamp=candidate_discharge_time,
        )
        unresolved_vitals = sorted(
            set(unresolved_details.get("unresolved_vitals", []))
            | set(latest_abnormal_vitals)
        )
        debug_payload["unresolved_alerts_after_final_treatment"] = {
            "exists": bool(unresolved_vitals),
            "unresolved_vitals": unresolved_vitals,
        }
        debug_payload["unresolved_abnormal_vitals"] = unresolved_vitals
        if unresolved_vitals:
            reason_lines = []
            for vital_key in unresolved_vitals:
                latest_abnormal = (unresolved_details.get("latest_abnormal_by_vital") or {}).get(vital_key)
                debug_alert = latest_alert_debug.get(vital_key) if isinstance(latest_alert_debug.get(vital_key), dict) else None
                canonical = (
                    normalize_alert_type(latest_abnormal.alert_type, latest_abnormal.severity)
                    if latest_abnormal is not None
                    else (debug_alert or {}).get("type", "unknown")
                )
                ts = (
                    latest_abnormal.created_at.isoformat()
                    if latest_abnormal is not None
                    else (((debug_alert or {}).get("timestamp") or "unknown"))
                )
                vital_label = vital_key.replace("_saturation", "")
                reason_lines.append(
                    f"Blocked recovered discharge because latest {vital_label} alert is {canonical} at {ts} and no newer normalized alert exists."
                )
            debug_payload["reason"] = " ".join(reason_lines)
            return False, "unresolved_abnormal_alerts_after_effective_treatment", debug_payload

        if required_stability_window_seconds > 0:
            if stability_started_at is None:
                debug_payload["reason"] = "Blocked recovered discharge because the stability window start is missing."
                return False, "stability_window_missing_start", debug_payload
            stable_seconds = (candidate_discharge_time - stability_started_at).total_seconds()
            debug_payload["stable_window_seconds"] = stable_seconds
            if stable_seconds < required_stability_window_seconds:
                debug_payload["reason"] = (
                    f"Blocked recovered discharge because stable window is {stable_seconds:.2f}s "
                    f"(<{required_stability_window_seconds}s)."
                )
                return False, "stability_window_not_satisfied", debug_payload

        debug_payload["reason"] = "Recovered discharge allowed: final treatment and latest vital/alert states are stable."
        return True, "ok", debug_payload
