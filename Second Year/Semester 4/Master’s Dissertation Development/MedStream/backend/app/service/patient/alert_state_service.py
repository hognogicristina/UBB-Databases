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




class PatientAlertStateService:
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

    @classmethod
    def _classify_alert_state(cls, canonical_type: str) -> str:
        normalized = str(canonical_type or "").strip().lower()
        if not normalized:
            return "none"

        if normalized in cls.ABNORMAL_ALERT_TYPES:
            return "abnormal"
        if normalized in cls.RECOVERY_ALERT_TYPES:
            return "normalized"

        # Fallback classification for legacy/variant canonical values.
        if normalized.startswith(("heart_rate_", "oxygen_", "temperature_")):
            if normalized.endswith(("_high", "_critical", "_low")):
                return "abnormal"
            if normalized.endswith(("_normalized", "_normal", "_stable")):
                return "normalized"

        return "none"
    @classmethod
    def _classify_vital_alert_state(cls, canonical_type: str) -> str:
        return cls._classify_alert_state(canonical_type)
    @staticmethod
    def _extract_status_vitals(message: str | None) -> dict | None:
        import re

        alert_message = str(message or "")
        hr_match = re.search(r"(?:heart\s*rate|HR)\D*(-?\d+(?:\.\d+)?)", alert_message, re.IGNORECASE)
        o2_match = re.search(r"(?:SpO2|oxygen)\D*(-?\d+(?:\.\d+)?)", alert_message, re.IGNORECASE)
        temp_match = re.search(r"(?:temp(?:erature)?)\D*(-?\d+(?:\.\d+)?)", alert_message, re.IGNORECASE)

        if hr_match is None and o2_match is None and temp_match is None:
            return None

        def to_float(match):
            if match is None:
                return None
            try:
                return float(match.group(1))
            except ValueError:
                return None

        return {
            "heartRate": to_float(hr_match),
            "oxygen": to_float(o2_match),
            "temperature": to_float(temp_match),
        }
    @classmethod
    def _extract_alert_structured_fields(cls, alert_type: str | None, message: str | None, severity: str | None) -> tuple[
        str | None, float | None, str | None, dict | None]:
        canonical_type = normalize_alert_type(alert_type, severity)
        alert_message = str(message or "")

        if canonical_type.endswith("_normalized"):
            status_vitals = cls._extract_status_vitals(alert_message)
            base_vital = vital_for_alert_type(canonical_type)
            base_type = base_vital if base_vital != "oxygen" else "oxygen_saturation"
            value = None
            unit = None
            if status_vitals is not None:
                if base_vital == "heart_rate":
                    value = status_vitals.get("heartRate")
                    unit = "bpm"
                elif base_vital == "oxygen":
                    value = status_vitals.get("oxygen")
                    unit = "%"
                elif base_vital == "temperature":
                    value = status_vitals.get("temperature")
                    unit = "C"
            return base_type, value, unit, status_vitals

        vital = vital_for_alert_type(canonical_type)
        if vital is None:
            return None, None, None, None

        import re
        if vital == "heart_rate":
            match = re.search(r"(?:heart\s*rate|HR)\D*(-?\d+(?:\.\d+)?)", alert_message, re.IGNORECASE)
            unit = "bpm"
            result_type = "heart_rate"
        elif vital == "oxygen":
            match = re.search(r"(?:SpO2|oxygen)\D*(-?\d+(?:\.\d+)?)", alert_message, re.IGNORECASE)
            unit = "%"
            result_type = "oxygen_saturation"
        else:
            match = re.search(r"(?:temp(?:erature)?)\D*(-?\d+(?:\.\d+)?)", alert_message, re.IGNORECASE)
            unit = "C"
            result_type = "temperature"

        if match is None:
            return result_type, None, unit, None

        try:
            value = float(match.group(1))
        except ValueError:
            value = None
        return result_type, value, unit, None
    @staticmethod
    def _normalize_datetime_for_comparison(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return to_utc(value)
    @classmethod
    def _normalize_datetime_candidates(cls, values: list[datetime | None]) -> list[datetime]:
        normalized: list[datetime] = []
        for value in values:
            normalized_value = cls._normalize_datetime_for_comparison(value)
            if normalized_value is not None:
                normalized.append(normalized_value)
        return normalized
    @classmethod
    def _get_latest_vital_specific_alert_state(
            cls,
            *,
            sequence_alerts: list[Alert],
            window_start: datetime | None = None,
            window_end: datetime,
    ) -> dict[str, dict[str, Any]]:
        normalized_window_start = cls._normalize_datetime_for_comparison(window_start)
        normalized_window_end = cls._normalize_datetime_for_comparison(window_end)
        if normalized_window_end is None:
            return {
                "heart_rate": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
                "oxygen_saturation": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
                "temperature": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
            }

        state = {
            "heart_rate": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
            "oxygen_saturation": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
            "temperature": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
        }

        for alert in sequence_alerts:
            alert_created_at = cls._normalize_datetime_for_comparison(alert.created_at)
            if alert_created_at is None:
                continue
            if normalized_window_start is not None and alert_created_at < normalized_window_start:
                continue
            if alert_created_at > normalized_window_end:
                continue
            canonical_type = normalize_alert_type(alert.alert_type, alert.severity)
            vital_key = vital_for_alert_type(canonical_type)
            if vital_key is None:
                continue
            mapped_vital_key = "oxygen_saturation" if vital_key == "oxygen" else vital_key
            bucket = state.get(mapped_vital_key)
            if bucket is None:
                continue

            bucket["latest"] = alert
            alert_state = cls._classify_alert_state(canonical_type)
            if alert_state == "normalized":
                bucket["latest_normalized"] = alert
                bucket["latest_state"] = "normalized"
            elif alert_state == "abnormal":
                bucket["latest_abnormal"] = alert
                bucket["latest_state"] = "abnormal"

        return state
    @classmethod
    def _build_latest_alert_debug_payload(
            cls,
            alert_state: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any] | None]:
        payload: dict[str, dict[str, Any] | None] = {}
        for vital_key in ("heart_rate", "oxygen_saturation", "temperature"):
            bucket = alert_state.get(vital_key) or {}
            latest_alert = bucket.get("latest")
            if latest_alert is None:
                payload[vital_key] = None
                continue

            canonical_type = normalize_alert_type(latest_alert.alert_type, latest_alert.severity)
            _, value, _, _ = cls._extract_alert_structured_fields(
                latest_alert.alert_type,
                latest_alert.message,
                latest_alert.severity,
            )
            payload[vital_key] = {
                "id": latest_alert.id,
                "type": canonical_type,
                "severity": latest_alert.severity,
                "timestamp": latest_alert.created_at,
                "value": value,
                "message": latest_alert.message,
                "state": str(bucket.get("latest_state") or cls._classify_alert_state(canonical_type) or "none"),
            }
        return payload
    @classmethod
    def _current_alert_level(cls, sequence_alerts: list[Alert]) -> str:
        if not sequence_alerts:
            return "none"

        alert_state = cls._get_latest_vital_specific_alert_state(
            sequence_alerts=sequence_alerts,
            window_end=now_utc(),
        )
        has_high = False
        has_normal = False

        for bucket in alert_state.values():
            latest_alert = bucket.get("latest")
            if latest_alert is None:
                continue

            latest_state = str(bucket.get("latest_state") or "none").strip().lower()
            if latest_state == "abnormal":
                canonical_type = normalize_alert_type(latest_alert.alert_type, latest_alert.severity)
                severity = str(latest_alert.severity or "").strip().lower()
                if severity == "critical" or canonical_type.endswith("_critical"):
                    return "critical"
                has_high = True
            elif latest_state == "normalized":
                has_normal = True

        if has_high:
            return "high"
        if has_normal:
            return "normal"
        return "none"
    @classmethod
    def _format_vital_label(cls, vital_key: str) -> str:
        normalized = str(vital_key or "").strip().lower()
        if normalized in cls.VITAL_LABELS:
            return cls.VITAL_LABELS[normalized]
        return normalized.replace("_", " ")
    @classmethod
    def _pick_most_problematic_vital(
            cls,
            abnormal_counts_by_vital: dict[str, int],
            total_counts_by_vital: dict[str, int],
    ) -> str:
        def pick_from(mapping: dict[str, int]) -> str | None:
            if not mapping:
                return None
            ordered = sorted(
                ((key, int(value or 0)) for key, value in mapping.items()),
                key=lambda item: (-item[1], cls.VITAL_PRIORITY.index(item[0]) if item[0] in cls.VITAL_PRIORITY else 999, item[0]),
            )
            return ordered[0][0] if ordered and ordered[0][1] > 0 else None

        most_problematic = pick_from(abnormal_counts_by_vital)
        if most_problematic is not None:
            return most_problematic

        fallback = pick_from(total_counts_by_vital)
        return fallback or "none"
    @classmethod
    def _safe_summary_text(cls, value: str | None, fallback: str) -> str:
        text = str(value or "").strip()
        return text if text else fallback
    @classmethod
    def _build_final_vital_state_text(cls, vital: Vital | None) -> str:
        if vital is None:
            return "No final vital snapshot available."
        return (
            f"Heart rate {vital.heart_rate} bpm, oxygen saturation {vital.oxygen_saturation}%, "
            f"temperature {vital.temperature}\N{DEGREE SIGN}C."
        )
    @classmethod
    def _get_unresolved_abnormal_vitals(
            cls,
            *,
            full_alert_state: dict[str, dict[str, Any]],
            unresolved_after_treatment_vitals: list[str],
    ) -> list[str]:
        unresolved_from_latest = [
            key
            for key, bucket in full_alert_state.items()
            if str((bucket or {}).get("latest_state") or "").strip().lower() == "abnormal"
        ]
        return sorted(set(unresolved_from_latest) | set(unresolved_after_treatment_vitals or []))
    @classmethod
    def _get_recovered_vitals_after_treatment(
            cls,
            *,
            sequence_alerts: list[Alert],
            window_start: datetime,
            window_end: datetime,
            post_treatment_alert_state: dict[str, dict[str, Any]],
            full_alert_state: dict[str, dict[str, Any]],
    ) -> list[str]:
        normalized_start = cls._normalize_datetime_for_comparison(window_start)
        normalized_end = cls._normalize_datetime_for_comparison(window_end)
        if normalized_start is None or normalized_end is None:
            return []

        latest_abnormal_at_or_before_end: dict[str, datetime] = {}
        for alert in sequence_alerts:
            alert_created_at = cls._normalize_datetime_for_comparison(alert.created_at)
            if alert_created_at is None or alert_created_at > normalized_end:
                continue
            canonical_type = normalize_alert_type(alert.alert_type, alert.severity)
            vital_key = vital_for_alert_type(canonical_type)
            if vital_key is None:
                continue
            mapped_vital_key = "oxygen_saturation" if vital_key == "oxygen" else vital_key
            if cls._classify_alert_state(canonical_type) == "abnormal":
                latest_abnormal_at_or_before_end[mapped_vital_key] = alert_created_at

        recovered: list[str] = []
        for vital_key in ("heart_rate", "oxygen_saturation", "temperature"):
            bucket = post_treatment_alert_state.get(vital_key) or {}
            latest_normalized = bucket.get("latest_normalized")
            if latest_normalized is None:
                continue

            normalized_at = cls._normalize_datetime_for_comparison(latest_normalized.created_at)
            if normalized_at is None or normalized_at <= normalized_start:
                continue

            latest_abnormal_at = latest_abnormal_at_or_before_end.get(vital_key)
            if latest_abnormal_at is None or latest_abnormal_at >= normalized_at:
                continue

            latest_full_state = str((full_alert_state.get(vital_key) or {}).get("latest_state") or "").strip().lower()
            if latest_full_state != "normalized":
                continue

            recovered.append(vital_key)

        return sorted(recovered)
    @classmethod
    def _find_complete_recovery_snapshot(
            cls,
            *,
            sequence_alerts: list[Alert],
            window_start: datetime,
            window_end: datetime,
    ) -> dict[str, Any] | None:
        normalized_start = cls._normalize_datetime_for_comparison(window_start)
        normalized_end = cls._normalize_datetime_for_comparison(window_end)
        if normalized_start is None or normalized_end is None:
            return None

        state = {
            "heart_rate": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
            "oxygen_saturation": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
            "temperature": {"latest": None, "latest_abnormal": None, "latest_normalized": None, "latest_state": "none"},
        }
        recovered_vitals: set[str] = set()

        for alert in sequence_alerts:
            alert_created_at = cls._normalize_datetime_for_comparison(alert.created_at)
            if alert_created_at is None:
                continue
            if alert_created_at > normalized_end:
                break

            canonical_type = normalize_alert_type(alert.alert_type, alert.severity)
            vital_key = vital_for_alert_type(canonical_type)
            if vital_key is None:
                continue

            mapped_vital_key = "oxygen_saturation" if vital_key == "oxygen" else vital_key
            bucket = state.get(mapped_vital_key)
            if bucket is None:
                continue

            bucket["latest"] = alert
            alert_state = cls._classify_alert_state(canonical_type)
            if alert_state == "normalized":
                bucket["latest_normalized"] = alert
                bucket["latest_state"] = "normalized"
                if alert_created_at > normalized_start:
                    recovered_vitals.add(mapped_vital_key)
            elif alert_state == "abnormal":
                bucket["latest_abnormal"] = alert
                bucket["latest_state"] = "abnormal"

            if alert_created_at <= normalized_start:
                continue

            unresolved_vitals = [
                key
                for key, current in state.items()
                if str((current or {}).get("latest_state") or "").strip().lower() == "abnormal"
            ]
            if recovered_vitals and not unresolved_vitals:
                return {
                    "recovered_at": alert.created_at,
                    "recovered_vitals": sorted(recovered_vitals),
                    "latest_alerts": cls._build_latest_alert_debug_payload(state),
                }

        return None
    @classmethod
    def _has_unresolved_abnormal_alerts_after_in_sequence(
            cls,
            *,
            sequence_alerts: list[Alert],
            after_timestamp: datetime,
            up_to_timestamp: datetime | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        normalized_after_timestamp = cls._normalize_datetime_for_comparison(after_timestamp)
        normalized_up_to_timestamp = cls._normalize_datetime_for_comparison(up_to_timestamp)
        if normalized_after_timestamp is None:
            return False, {
                "unresolved_vitals": [],
                "latest_abnormal_by_vital": {},
                "latest_recovery_by_vital": {},
            }

        unresolved_by_vital: dict[str, Alert] = {}
        latest_recovery_by_vital: dict[str, Alert] = {}
        latest_abnormal_by_vital: dict[str, Alert] = {}

        for alert in sequence_alerts:
            alert_created_at = cls._normalize_datetime_for_comparison(alert.created_at)
            if alert_created_at is None:
                continue
            if alert_created_at <= normalized_after_timestamp:
                continue
            if normalized_up_to_timestamp is not None and alert_created_at > normalized_up_to_timestamp:
                continue
            canonical_type = normalize_alert_type(alert.alert_type, alert.severity)
            vital_key = vital_for_alert_type(canonical_type)
            if vital_key is None:
                continue

            mapped_vital_key = "oxygen_saturation" if vital_key == "oxygen" else vital_key
            alert_state = cls._classify_alert_state(canonical_type)
            if alert_state == "abnormal":
                unresolved_by_vital[mapped_vital_key] = alert
                latest_abnormal_by_vital[mapped_vital_key] = alert
            elif alert_state == "normalized":
                latest_recovery_by_vital[mapped_vital_key] = alert
                unresolved_by_vital.pop(mapped_vital_key, None)

        return bool(unresolved_by_vital), {
            "unresolved_vitals": sorted(unresolved_by_vital.keys()),
            "latest_abnormal_by_vital": latest_abnormal_by_vital,
            "latest_recovery_by_vital": latest_recovery_by_vital,
        }
    @classmethod
    def get_latest_vital_state(
            cls,
            db,
            patient_id: int,
            *,
            up_to_timestamp: datetime | None = None,
    ) -> Vital | None:
        query = select(Vital).where(Vital.patient_id == patient_id)
        if up_to_timestamp is not None:
            query = query.where(Vital.recorded_at <= up_to_timestamp)
        return db.execute(
            query.order_by(Vital.recorded_at.desc(), Vital.id.desc()).limit(1)
        ).scalar_one_or_none()
    @classmethod
    def get_latest_vital_alert_state(
            cls,
            db,
            patient_id: int,
            *,
            up_to_timestamp: datetime | None = None,
    ) -> dict[str, dict[str, Any]]:
        alerts = db.execute(
            select(Alert)
            .where(Alert.patient_id == patient_id)
            .order_by(Alert.created_at.asc(), Alert.id.asc())
        ).scalars().all()
        end_time = up_to_timestamp or now_utc()
        return cls._get_latest_vital_specific_alert_state(
            sequence_alerts=alerts,
            window_end=end_time,
        )
    @classmethod
    def has_unresolved_abnormal_alerts_after(
            cls,
            db,
            patient_id: int,
            timestamp: datetime,
            *,
            up_to_timestamp: datetime | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        alerts = db.execute(
            select(Alert)
            .where(Alert.patient_id == patient_id)
            .order_by(Alert.created_at.asc(), Alert.id.asc())
        ).scalars().all()
        return cls._has_unresolved_abnormal_alerts_after_in_sequence(
            sequence_alerts=alerts,
            after_timestamp=timestamp,
            up_to_timestamp=up_to_timestamp,
        )
