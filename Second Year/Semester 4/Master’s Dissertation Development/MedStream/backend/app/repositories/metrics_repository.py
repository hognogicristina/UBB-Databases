from collections import Counter, deque
from datetime import timedelta
from math import ceil
from threading import Lock
from time import perf_counter

from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.batch.status import batch_status_store, utc_now
from app.models.alert import Alert
from app.models.batch_analytics import BatchAnalytics
from app.models.comparison_metric_sample import ComparisonMetricSample
from app.models.patient.patient import Patient
from app.models.patient.patient_condition_assignment import PatientConditionAssignment
from app.models.patient.patient_diagnosis import PatientDiagnosis
from app.models.patient.patient_discharge_summary import PatientDischargeSummary
from app.models.patient.patient_medication import PatientMedication
from app.models.patient.patient_stats import PatientStats
from app.models.vital import Vital
from app.repositories.patient_repository import PatientRepository
from app.utils.datetime import to_utc
from app.validators.metrics_validators import validate_metric_value

WINDOW_MINUTES = 60
WINDOW_DELTA = timedelta(minutes=WINDOW_MINUTES)
HISTORY_INTERVAL_SECONDS = 4
HISTORY_MAX_POINTS = 900
HISTORY_ALERT_WINDOW_SECONDS = 60
HISTORY_ALERT_WINDOW_DELTA = timedelta(seconds=HISTORY_ALERT_WINDOW_SECONDS)
METRIC_SAMPLE_RETENTION_HOURS = 6


def _empty_metrics():
    return {
        "avg_heart_rate": 0.0,
        "avg_oxygen": 0.0,
        "avg_temperature": 0.0,
        "avg_systolic_bp": None,
        "avg_diastolic_bp": None,
        "total_alerts": 0,
        "alerts_critical_count": 0,
        "alerts_high_count": 0,
        "alerts_stable_count": 0,
        "active_patients": 0,
        "execution_time_ms": 0.0,
        "timestamp": None,
        "generated_discharge_summaries_count": 0,
        "pending_discharge_summaries_count": 0,
    }


def _empty_treatment_effectiveness():
    return {
        "effective": 0,
        "improving": 0,
        "ineffective": 0,
        "effective_rate": 0.0,
        "improving_rate": 0.0,
        "ineffective_rate": 0.0,
    }


def _empty_insights_snapshot():
    return {
        "patients_per_department": [],
        "top_diagnosis": [],
        "treatment_effectiveness": _empty_treatment_effectiveness(),
        "medication_effectiveness": [],
    }


class StreamingMetricsStore:
    def __init__(self):
        self._lock = Lock()
        self._vitals = deque()
        self._alerts = deque()
        self._recent_alerts = deque(maxlen=10)
        self._patient_counts = Counter()
        self._heart_rate_sum = 0.0
        self._oxygen_sum = 0.0
        self._temperature_sum = 0.0
        self._last_execution_time_ms = 0.0

    def record_vital(self, vital, alert_count: int):
        started_at = perf_counter()
        cutoff = utc_now() - WINDOW_DELTA

        with self._lock:
            self._vitals.append(
                (
                    to_utc(vital.recorded_at),
                    vital.patient_id,
                    vital.heart_rate,
                    vital.oxygen_saturation,
                    vital.temperature,
                    alert_count,
                )
            )
            self._heart_rate_sum += vital.heart_rate
            self._oxygen_sum += vital.oxygen_saturation
            self._temperature_sum += vital.temperature
            self._patient_counts[vital.patient_id] += 1

            self._purge_expired(cutoff)
            self._last_execution_time_ms = round((perf_counter() - started_at) * 1000, 2)

    def record_alert(self, alert):
        cutoff = utc_now() - WINDOW_DELTA

        with self._lock:
            self._alerts.append(to_utc(alert.created_at))
            self._recent_alerts.appendleft(
                {
                    "id": alert.id,
                    "patient_id": alert.patient_id,
                    "vital_id": alert.vital_id,
                    "alert_type": alert.alert_type,
                    "message": alert.message,
                    "severity": alert.severity,
                    "created_at": to_utc(alert.created_at),
                }
            )
            self._purge_expired_alerts(cutoff)

    def snapshot(self, vitals_limit: int = 30):
        cutoff = utc_now() - WINDOW_DELTA

        with self._lock:
            self._purge_expired(cutoff)
            self._purge_expired_alerts(cutoff)
            count = len(self._vitals)
            recent_vitals = list(self._vitals)[-max(1, vitals_limit):]

            return {
                "avg_heart_rate": validate_metric_value(self._heart_rate_sum / count) if count else 0.0,
                "avg_oxygen": validate_metric_value(self._oxygen_sum / count) if count else 0.0,
                "avg_temperature": validate_metric_value(self._temperature_sum / count) if count else 0.0,
                "total_alerts": len(self._alerts),
                "active_patients": len(self._patient_counts),
                "execution_time_ms": self._last_execution_time_ms,
                "recent_vitals": [
                    {
                        "recorded_at": to_utc(recorded_at),
                        "patient_id": patient_id,
                        "heart_rate": heart_rate,
                        "oxygen_saturation": oxygen,
                        "temperature": temperature,
                    }
                    for recorded_at, patient_id, heart_rate, oxygen, temperature, _ in recent_vitals
                ],
            }

    def alerts_snapshot(self, page: int, page_size: int):
        with self._lock:
            items = list(self._recent_alerts)
            paginated = paginate_items(items, page, page_size)
            paginated["items"] = [
                {
                    **item,
                    "created_at": to_utc(item["created_at"]),
                }
                for item in paginated["items"]
            ]
            return paginated

    def _purge_expired(self, cutoff):
        while self._vitals and to_utc(self._vitals[0][0]) < cutoff:
            _, patient_id, heart_rate, oxygen, temperature, _ = self._vitals.popleft()
            self._heart_rate_sum -= heart_rate
            self._oxygen_sum -= oxygen
            self._temperature_sum -= temperature
            self._patient_counts[patient_id] -= 1

            if self._patient_counts[patient_id] <= 0:
                del self._patient_counts[patient_id]

    def _purge_expired_alerts(self, cutoff):
        while self._alerts and to_utc(self._alerts[0]) < cutoff:
            self._alerts.popleft()


def paginate_items(items, page: int, page_size: int):
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _apply_patient_treatment_outcomes(db: Session, patient_treatment_outcomes: list[dict]):
    if not patient_treatment_outcomes:
        return

    outcomes_by_patient_id = {
        int(item["patient_id"]): ",".join(item.get("outcomes") or [])
        for item in patient_treatment_outcomes
        if item.get("patient_id") is not None
    }
    if not outcomes_by_patient_id:
        return

    stats_rows = db.execute(
        select(PatientStats).where(PatientStats.patient_id.in_(outcomes_by_patient_id.keys()))
    ).scalars().all()
    for stat in stats_rows:
        stat.treatment_outcomes = outcomes_by_patient_id.get(int(stat.patient_id), "")


def refresh_batch_snapshot(db: Session, execution_time_ms: float):
    snapshot_timestamp = utc_now()
    insights_snapshot = build_batch_insights_snapshot(db)
    window_start = snapshot_timestamp - WINDOW_DELTA
    window_seconds = max(1, int(WINDOW_DELTA.total_seconds()))
    _apply_patient_treatment_outcomes(db, insights_snapshot.get("patient_treatment_outcomes", []))
    metrics_row = db.execute(
        select(
            func.avg(PatientStats.avg_heart_rate),
            func.avg(PatientStats.avg_oxygen),
            func.avg(PatientStats.avg_temperature),
            func.sum(PatientStats.alerts_count),
            func.count(PatientStats.patient_id),
        )
    ).one()
    bp_row = db.execute(
        select(
            func.avg(Vital.systolic_bp),
            func.avg(Vital.diastolic_bp),
        )
    ).one()
    total_events_count = int(
        db.execute(
            select(func.count(Vital.id)).where(
                Vital.recorded_at >= window_start,
                Vital.recorded_at <= snapshot_timestamp,
            )
        ).scalar_one()
        or 0
    )
    batch_latency_seconds = db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    snapshot_timestamp - Vital.recorded_at,
                )
            )
        )
        .select_from(Vital)
        .where(
            Vital.recorded_at >= window_start,
            Vital.recorded_at <= snapshot_timestamp,
        )
    ).scalar_one()
    alert_severity_rows = db.execute(
        select(Alert.severity, func.count(Alert.id))
        .where(
            Alert.created_at >= window_start,
            Alert.created_at <= snapshot_timestamp,
        )
        .group_by(Alert.severity)
    ).all()

    severity_counts = {"critical": 0, "high": 0, "stable": 0}
    for severity, count in alert_severity_rows:
        normalized = str(severity or "").strip().lower()
        if normalized == "critical":
            severity_counts["critical"] += int(count or 0)
        elif normalized == "high":
            severity_counts["high"] += int(count or 0)
        else:
            severity_counts["stable"] += int(count or 0)

    batch_row = BatchAnalytics(
        timestamp=snapshot_timestamp,
        avg_heart_rate=validate_metric_value(metrics_row[0]),
        avg_oxygen=validate_metric_value(metrics_row[1]),
        avg_temperature=validate_metric_value(metrics_row[2]),
        avg_systolic_bp=float(bp_row[0]) if bp_row[0] is not None else None,
        avg_diastolic_bp=float(bp_row[1]) if bp_row[1] is not None else None,
        alerts_count=int(metrics_row[3] or 0),
        alerts_critical_count=severity_counts["critical"],
        alerts_high_count=severity_counts["high"],
        alerts_stable_count=severity_counts["stable"],
        patients_count=int(metrics_row[4] or 0),
        total_events_count=total_events_count,
        events_per_second=round(total_events_count / window_seconds, 4),
        alert_rate=round((int(metrics_row[3] or 0) / total_events_count), 4) if total_events_count > 0 else 0.0,
        batch_latency_avg_seconds=round(float(batch_latency_seconds or 0), 2),
        patients_per_department_snapshot=insights_snapshot["patients_per_department"],
        top_diagnosis_snapshot=insights_snapshot["top_diagnosis"],
        treatment_effectiveness_snapshot=insights_snapshot["treatment_effectiveness"],
        medication_effectiveness_snapshot=insights_snapshot["medication_effectiveness"],
    )
    db.add(batch_row)

    db.commit()

    return {
        "avg_heart_rate": batch_row.avg_heart_rate,
        "avg_oxygen": batch_row.avg_oxygen,
        "avg_temperature": batch_row.avg_temperature,
        "avg_systolic_bp": batch_row.avg_systolic_bp,
        "avg_diastolic_bp": batch_row.avg_diastolic_bp,
        "total_alerts": batch_row.alerts_count,
        "alerts_critical_count": batch_row.alerts_critical_count,
        "alerts_high_count": batch_row.alerts_high_count,
        "alerts_stable_count": batch_row.alerts_stable_count,
        "active_patients": batch_row.patients_count,
        "execution_time_ms": round(float(execution_time_ms or 0), 2),
        "timestamp": snapshot_timestamp,
    }


def get_latest_batch_analytics(db: Session) -> BatchAnalytics | None:
    return db.execute(
        select(BatchAnalytics)
        .order_by(BatchAnalytics.timestamp.desc(), BatchAnalytics.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def get_latest_batch_metrics(db: Session) -> dict:
    latest = get_latest_batch_analytics(db)
    if latest is None:
        return _empty_metrics()

    status_snapshot = batch_status_store.snapshot()
    generated_discharge_summaries_count = int(
        db.execute(select(func.count(PatientDischargeSummary.id))).scalar_one() or 0
    )
    pending_discharge_summaries_count = int(
        db.execute(
            select(func.count(Patient.id))
            .where(Patient.is_discharged.is_(True), Patient.discharge_date.is_not(None))
            .where(
                ~select(PatientDischargeSummary.id)
                .where(
                    PatientDischargeSummary.patient_id == Patient.id,
                    PatientDischargeSummary.discharge_date == Patient.discharge_date,
                )
                .exists()
            )
        ).scalar_one() or 0
    )

    return {
        "avg_heart_rate": validate_metric_value(latest.avg_heart_rate),
        "avg_oxygen": validate_metric_value(latest.avg_oxygen),
        "avg_temperature": validate_metric_value(latest.avg_temperature),
        "avg_systolic_bp": float(latest.avg_systolic_bp) if latest.avg_systolic_bp is not None else None,
        "avg_diastolic_bp": float(latest.avg_diastolic_bp) if latest.avg_diastolic_bp is not None else None,
        "total_alerts": int(latest.alerts_count or 0),
        "alerts_critical_count": int(latest.alerts_critical_count or 0),
        "alerts_high_count": int(latest.alerts_high_count or 0),
        "alerts_stable_count": int(latest.alerts_stable_count or 0),
        "active_patients": int(latest.patients_count or 0),
        "execution_time_ms": round(float(status_snapshot.get("last_run_duration_ms") or 0), 2),
        "timestamp": to_utc(latest.timestamp),
        "generated_discharge_summaries_count": generated_discharge_summaries_count,
        "pending_discharge_summaries_count": pending_discharge_summaries_count,
    }


def get_batch_alerts_history(db: Session, *, limit: int = 24) -> list[dict]:
    rows = db.execute(
        select(BatchAnalytics)
        .order_by(BatchAnalytics.timestamp.desc(), BatchAnalytics.id.desc())
        .limit(limit)
    ).scalars().all()

    ordered = list(reversed(rows))
    return [
        {
            "timestamp": to_utc(row.timestamp),
            "critical": int(row.alerts_critical_count or 0),
            "high": int(row.alerts_high_count or 0),
            "stable": int(row.alerts_stable_count or 0),
            "normalized": int(row.alerts_stable_count or 0),
            "total": int(row.alerts_count or 0),
        }
        for row in ordered
    ]


def get_comparison_metrics(db: Session) -> dict:
    now = utc_now()
    window_start = now - WINDOW_DELTA
    window_seconds = max(1, int(WINDOW_DELTA.total_seconds()))

    total_events = int(
        db.execute(
            select(func.count(Vital.id)).where(Vital.recorded_at >= window_start)
        ).scalar_one()
        or 0
    )
    total_alerts = int(
        db.execute(
            select(func.count(Alert.id)).where(Alert.created_at >= window_start)
        ).scalar_one()
        or 0
    )

    streaming_latency_seconds = db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Alert.created_at - Vital.recorded_at,
                )
            )
        )
        .select_from(Alert)
        .join(Vital, Vital.id == Alert.vital_id)
        .where(
            Alert.created_at >= window_start,
            Vital.recorded_at.is_not(None),
        )
    ).scalar_one()

    latest_batch = get_latest_batch_analytics(db)
    batch_total_events = int(latest_batch.total_events_count or 0) if latest_batch is not None else 0
    batch_total_alerts = int(latest_batch.alerts_count or 0) if latest_batch is not None else 0

    return {
        "streaming_latency_avg": round(float((streaming_latency_seconds or 0) * 1000), 2),
        "batch_latency_avg": round(float(latest_batch.batch_latency_avg_seconds or 0), 2) if latest_batch is not None else 0.0,
        "total_events": total_events,
        "total_alerts": total_alerts,
        "events_per_second": round(total_events / window_seconds, 4),
        "alert_rate": round((total_alerts / total_events), 4) if total_events > 0 else 0.0,
        "batch_total_events": batch_total_events,
        "batch_total_alerts": batch_total_alerts,
        "batch_events_per_second": round(float(latest_batch.events_per_second or 0), 4) if latest_batch is not None else 0.0,
        "batch_alert_rate": round(float(latest_batch.alert_rate or 0), 4) if latest_batch is not None else 0.0,
    }


def record_comparison_metric_sample(db: Session, *, retention_hours: int = METRIC_SAMPLE_RETENTION_HOURS) -> dict:
    now = utc_now()
    window_start = now - HISTORY_ALERT_WINDOW_DELTA

    streaming_alerts_count = int(
        db.execute(
            select(func.count(Alert.id)).where(
                Alert.created_at >= window_start,
                Alert.created_at <= now,
            )
        ).scalar_one()
        or 0
    )
    streaming_latency_seconds = db.execute(
        select(
            func.avg(
                func.extract(
                    "epoch",
                    Alert.created_at - Vital.recorded_at,
                )
            )
        )
        .select_from(Alert)
        .join(Vital, Vital.id == Alert.vital_id)
        .where(
            Alert.created_at >= window_start,
            Alert.created_at <= now,
            Vital.recorded_at.is_not(None),
        )
    ).scalar_one()
    latest_batch = get_latest_batch_analytics(db)
    has_batch_snapshot = latest_batch is not None
    batch_window_alerts = (
        int(latest_batch.alerts_critical_count or 0)
        + int(latest_batch.alerts_high_count or 0)
        + int(latest_batch.alerts_stable_count or 0)
        if latest_batch is not None else None
    )
    batch_alerts_per_minute = (
        round(batch_window_alerts / max(1, WINDOW_MINUTES), 4)
        if batch_window_alerts is not None else None
    )

    sample = ComparisonMetricSample(
        timestamp=now,
        streaming_alerts_per_minute=streaming_alerts_count,
        batch_alerts_per_minute=batch_alerts_per_minute,
        streaming_latency_ms=round(float((streaming_latency_seconds or 0) * 1000), 2),
        batch_latency_ms=round(float(latest_batch.batch_latency_avg_seconds or 0) * 1000, 2)
        if latest_batch is not None else None,
        batch_timestamp=to_utc(latest_batch.timestamp) if latest_batch is not None else None,
        has_batch_snapshot=has_batch_snapshot,
    )
    db.add(sample)

    retention_cutoff = now - timedelta(hours=max(1, int(retention_hours or METRIC_SAMPLE_RETENTION_HOURS)))
    db.execute(delete(ComparisonMetricSample).where(ComparisonMetricSample.timestamp < retention_cutoff))
    db.commit()
    db.refresh(sample)

    return {
        "time_iso": to_utc(sample.timestamp),
        "time": to_utc(sample.timestamp).strftime("%H:%M:%S"),
        "streaming_alerts_per_minute": int(sample.streaming_alerts_per_minute or 0),
        "batch_alerts_per_minute": sample.batch_alerts_per_minute,
        "streaming_latency_ms": round(float(sample.streaming_latency_ms or 0), 2),
        "batch_latency_ms": sample.batch_latency_ms,
        "batch_timestamp": to_utc(sample.batch_timestamp),
        "has_batch_snapshot": bool(sample.has_batch_snapshot),
    }


def _downsample_history_rows(rows: list[ComparisonMetricSample], *, range_start, interval_seconds: int):
    if len(rows) <= HISTORY_MAX_POINTS:
        return rows

    buckets = {}
    for row in rows:
        bucket_index = int(max(0, (to_utc(row.timestamp) - range_start).total_seconds()) // interval_seconds)
        buckets[bucket_index] = row

    sampled_rows = list(buckets.values())
    if len(sampled_rows) <= HISTORY_MAX_POINTS:
        return sampled_rows

    step = ceil(len(sampled_rows) / HISTORY_MAX_POINTS)
    reduced_rows = sampled_rows[::step]
    if sampled_rows[-1] is not reduced_rows[-1]:
        reduced_rows[-1] = sampled_rows[-1]

    return reduced_rows


def get_comparison_history(
        db: Session,
        *,
        seconds: int = 3600,
        interval_seconds: int = HISTORY_INTERVAL_SECONDS,
        start_time=None,
        end_time=None,
) -> dict:
    now = utc_now()
    safe_interval_seconds = max(1, int(interval_seconds or HISTORY_INTERVAL_SECONDS))
    if start_time is not None and end_time is not None:
        range_start = to_utc(start_time)
        range_end = min(to_utc(end_time), now)
        if range_start >= range_end:
            rows = []
        else:
            safe_seconds = max(safe_interval_seconds, int((range_end - range_start).total_seconds()))
            safe_interval_seconds = max(safe_interval_seconds, ceil(safe_seconds / max(1, HISTORY_MAX_POINTS - 1)))
            rows = db.execute(
                select(ComparisonMetricSample)
                .where(
                    ComparisonMetricSample.timestamp >= range_start,
                    ComparisonMetricSample.timestamp <= range_end,
                )
                .order_by(ComparisonMetricSample.timestamp.asc(), ComparisonMetricSample.id.asc())
            ).scalars().all()
            rows = _downsample_history_rows(rows, range_start=range_start, interval_seconds=safe_interval_seconds)
    else:
        safe_seconds = max(safe_interval_seconds, int(seconds or safe_interval_seconds))
        range_end = now
        range_start = now - timedelta(seconds=safe_seconds)
        safe_interval_seconds = max(safe_interval_seconds, ceil(safe_seconds / max(1, HISTORY_MAX_POINTS - 1)))
        rows = db.execute(
            select(ComparisonMetricSample)
            .where(
                ComparisonMetricSample.timestamp >= range_start,
                ComparisonMetricSample.timestamp <= range_end,
            )
            .order_by(ComparisonMetricSample.timestamp.asc(), ComparisonMetricSample.id.asc())
        ).scalars().all()
        rows = _downsample_history_rows(rows, range_start=range_start, interval_seconds=safe_interval_seconds)

    rows = list(rows)
    throughput = [
        {
            "time_iso": to_utc(row.timestamp),
            "time": to_utc(row.timestamp).strftime("%H:%M:%S"),
            "streaming_alerts_per_minute": int(row.streaming_alerts_per_minute or 0),
            "batch_alerts_per_minute": row.batch_alerts_per_minute,
            "batch_timestamp": to_utc(row.batch_timestamp),
            "has_batch_snapshot": bool(row.has_batch_snapshot),
        }
        for row in rows
    ]
    latency = [
        {
            "time_iso": to_utc(row.timestamp),
            "time": to_utc(row.timestamp).strftime("%H:%M:%S"),
            "streaming_latency_ms": round(float(row.streaming_latency_ms or 0), 2),
            "batch_latency_ms": row.batch_latency_ms,
            "has_batch_snapshot": bool(row.has_batch_snapshot),
        }
        for row in rows
    ]

    return {
        "throughput": throughput,
        "latency": latency,
    }


def build_batch_insights_snapshot(db: Session) -> dict:
    department_rows = db.execute(
        select(Patient.department, func.count(PatientStats.patient_id))
        .join(PatientStats, PatientStats.patient_id == Patient.id)
        .group_by(Patient.department)
        .order_by(desc(func.count(PatientStats.patient_id)), Patient.department.asc())
    ).all()

    top_diagnosis_rows = db.execute(
        select(PatientDiagnosis.diagnosis, func.count(func.distinct(PatientDiagnosis.patient_id)).label("patient_count"))
        .join(PatientStats, PatientStats.patient_id == PatientDiagnosis.patient_id)
        .where(PatientDiagnosis.status == "active")
        .group_by(PatientDiagnosis.diagnosis)
        .order_by(desc("patient_count"), PatientDiagnosis.diagnosis.asc())
    ).all()

    medications = db.execute(
        select(PatientMedication)
        .order_by(PatientMedication.created_at.asc(), PatientMedication.id.asc())
    ).scalars().all()
    alerts = db.execute(
        select(Alert)
        .order_by(Alert.created_at.asc(), Alert.id.asc())
    ).scalars().all()
    vitals = db.execute(
        select(Vital)
        .order_by(Vital.recorded_at.asc(), Vital.id.asc())
    ).scalars().all()
    diagnosis_rows = db.execute(
        select(PatientDiagnosis.patient_id)
    ).all()
    condition_rows = db.execute(
        select(PatientConditionAssignment.patient_id)
    ).all()

    diagnoses_by_patient = {patient_id for (patient_id,) in diagnosis_rows}
    conditions_by_patient = {patient_id for (patient_id,) in condition_rows}
    patient_ids = sorted(
        set(int(item.patient_id) for item in medications if item.patient_id is not None)
        | set(int(item.patient_id) for item in alerts if item.patient_id is not None)
        | set(int(item.patient_id) for item in vitals if item.patient_id is not None)
    )
    patients_by_id = {}
    if patient_ids:
        patients = db.execute(
            select(Patient).where(Patient.id.in_(patient_ids))
        ).scalars().all()
        patients_by_id = {int(patient.id): patient for patient in patients}

    medications_by_patient: dict[int, list[PatientMedication]] = {}
    for medication in medications:
        medications_by_patient.setdefault(int(medication.patient_id), []).append(medication)

    alerts_by_patient: dict[int, list[Alert]] = {}
    for alert in alerts:
        alerts_by_patient.setdefault(int(alert.patient_id), []).append(alert)

    vitals_by_patient: dict[int, list[Vital]] = {}
    for vital in vitals:
        vitals_by_patient.setdefault(int(vital.patient_id), []).append(vital)

    medication_effectiveness: dict[str, dict] = {}
    patient_treatment_outcomes: dict[int, set[str]] = {}
    treatment_effective_total = 0
    treatment_improving_total = 0
    treatment_ineffective_total = 0
    for patient_id, patient_medications in medications_by_patient.items():
        if not patient_medications:
            continue
        patient = patients_by_id.get(patient_id)
        if patient is None:
            continue

        patient_alerts = alerts_by_patient.get(patient_id, [])
        patient_vitals = vitals_by_patient.get(patient_id, [])
        treatment_actions = PatientRepository.build_treatment_actions(patient_medications)
        if not treatment_actions:
            continue

        for action_index, action_entry in enumerate(treatment_actions):
            medication = action_entry["medication"]
            medication_name = str(medication.name or "").strip()
            if not medication_name:
                continue

            evaluation = PatientRepository.evaluate_treatment_action(
                patient=patient,
                action_index=action_index,
                treatment_actions=treatment_actions,
                sequence_vitals=patient_vitals,
                sequence_alerts=patient_alerts,
            )
            outcome = str(evaluation.get("outcome") or "Ineffective").strip()

            if medication_name not in medication_effectiveness:
                medication_effectiveness[medication_name] = {
                    "effective": 0,
                    "improving": 0,
                    "ineffective": 0,
                    "patients": set(),
                    "alert_triggered_count": 0,
                    "diagnosis_triggered_count": 0,
                    "condition_triggered_count": 0,
                    "dosage_breakdown": {},
                }

            entry = medication_effectiveness[medication_name]
            entry["patients"].add(patient_id)

            dosage_key = (medication.dosage or "--", medication.frequency or "--")
            entry["dosage_breakdown"][dosage_key] = entry["dosage_breakdown"].get(dosage_key, 0) + 1

            if outcome != "Effective":
                entry["alert_triggered_count"] += 1
            if patient_id in diagnoses_by_patient:
                entry["diagnosis_triggered_count"] += 1
            if patient_id in conditions_by_patient:
                entry["condition_triggered_count"] += 1

            if outcome == "Effective":
                entry["effective"] += 1
                treatment_effective_total += 1
                patient_treatment_outcomes.setdefault(patient_id, set()).add("effective")
            elif outcome == "Improving":
                entry["improving"] += 1
                treatment_improving_total += 1
                patient_treatment_outcomes.setdefault(patient_id, set()).add("improving")
            else:
                entry["ineffective"] += 1
                treatment_ineffective_total += 1
                patient_treatment_outcomes.setdefault(patient_id, set()).add("ineffective")

    total_treatments = treatment_effective_total + treatment_improving_total + treatment_ineffective_total

    return {
        "patients_per_department": [
            {"department": department, "patients": int(patients)}
            for department, patients in department_rows
        ],
        "top_diagnosis": [
            {
                "name": diagnosis,
                "patients": int(patient_count),
            }
            for diagnosis, patient_count in top_diagnosis_rows
        ],
        "treatment_effectiveness": {
            "effective": treatment_effective_total,
            "improving": treatment_improving_total,
            "ineffective": treatment_ineffective_total,
            "effective_rate": round((treatment_effective_total / total_treatments) * 100, 2) if total_treatments else 0.0,
            "improving_rate": round((treatment_improving_total / total_treatments) * 100, 2) if total_treatments else 0.0,
            "ineffective_rate": round((treatment_ineffective_total / total_treatments) * 100, 2) if total_treatments else 0.0,
        },
        "patient_treatment_outcomes": [
            {
                "patient_id": patient_id,
                "outcomes": sorted(outcomes),
            }
            for patient_id, outcomes in sorted(patient_treatment_outcomes.items())
        ],
        "medication_effectiveness": sorted(
            [
                {
                    "name": name,
                    "effective": values["effective"],
                    "improving": values["improving"],
                    "ineffective": values["ineffective"],
                    "total": values["effective"] + values["improving"] + values["ineffective"],
                    "effective_rate": round(
                        (values["effective"] / max(1, values["effective"] + values["improving"] + values["ineffective"])) * 100,
                        2,
                    ),
                    "improving_rate": round(
                        (values["improving"] / max(1, values["effective"] + values["improving"] + values["ineffective"])) * 100,
                        2,
                    ),
                    "ineffective_rate": round(
                        (values["ineffective"] / max(1, values["effective"] + values["improving"] + values["ineffective"])) * 100,
                        2,
                    ),
                    "total_patients": len(values["patients"]),
                    "alert_triggered_count": values["alert_triggered_count"],
                    "diagnosis_triggered_count": values["diagnosis_triggered_count"],
                    "condition_triggered_count": values["condition_triggered_count"],
                    "dosage_breakdown": [
                        {
                            "dosage": dosage,
                            "frequency": frequency,
                            "count": count,
                        }
                        for (dosage, frequency), count in values["dosage_breakdown"].items()
                    ],
                }
                for name, values in medication_effectiveness.items()
            ],
            key=lambda item: (-item["total"], item["name"]),
        ),
    }


def get_batch_insights_repo(db: Session, *, departments_page: int, diagnoses_page: int, page_size: int) -> dict:
    latest = get_latest_batch_analytics(db)
    snapshot = _empty_insights_snapshot()
    if latest is not None:
        snapshot = {
            "patients_per_department": list(latest.patients_per_department_snapshot or []),
            "top_diagnosis": list(latest.top_diagnosis_snapshot or []),
            "treatment_effectiveness": {
                **_empty_treatment_effectiveness(),
                **(latest.treatment_effectiveness_snapshot or {}),
            },
            "medication_effectiveness": list(latest.medication_effectiveness_snapshot or []),
        }

    return {
        "patients_per_department": paginate_items(snapshot["patients_per_department"], departments_page, page_size),
        "top_diagnosis": paginate_items(snapshot["top_diagnosis"], diagnoses_page, page_size),
        "treatment_effectiveness": snapshot["treatment_effectiveness"],
        "medication_effectiveness": snapshot["medication_effectiveness"],
    }


streaming_metrics_store = StreamingMetricsStore()
