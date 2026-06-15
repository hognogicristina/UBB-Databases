from sqlalchemy import func

from app.batch.status import utc_now
from app.db.session import SessionLocal
from app.models.alert import Alert
from app.models.patient.patient_stats import PatientStats
from app.models.vital import Vital
from app.repositories.patient_repository import PatientRepository
from app.service.metrics import WINDOW_DELTA


def _load_window_patient_vitals(db, window_start):
    return (
        db.query(
            Vital.patient_id,
            func.avg(Vital.heart_rate).label("avg_heart_rate"),
            func.avg(Vital.temperature).label("avg_temperature"),
            func.avg(Vital.oxygen_saturation).label("avg_oxygen"),
        )
        .filter(Vital.recorded_at >= window_start)
        .group_by(Vital.patient_id)
        .all()
    )


def _load_latest_available_patient_vitals(db, *, exclude_patient_ids=None):
    latest_vitals = (
        db.query(
            Vital.patient_id.label("patient_id"),
            func.max(Vital.recorded_at).label("latest_recorded_at"),
        )
        .group_by(Vital.patient_id)
        .subquery()
    )

    query = (
        db.query(
            Vital.patient_id,
            func.avg(Vital.heart_rate).label("avg_heart_rate"),
            func.avg(Vital.temperature).label("avg_temperature"),
            func.avg(Vital.oxygen_saturation).label("avg_oxygen"),
        )
        .join(
            latest_vitals,
            (Vital.patient_id == latest_vitals.c.patient_id)
            & (Vital.recorded_at == latest_vitals.c.latest_recorded_at),
        )
    )

    if exclude_patient_ids:
        query = query.filter(~Vital.patient_id.in_(exclude_patient_ids))

    return query.group_by(Vital.patient_id).all()


def _load_alert_counts(db, window_start):
    return {
        patient_id: alerts_count
        for patient_id, alerts_count in (
            db.query(Alert.patient_id, func.count(Alert.id))
            .filter(Alert.created_at >= window_start)
            .group_by(Alert.patient_id)
            .all()
        )
    }


def run():
    with SessionLocal() as db:
        window_start = utc_now() - WINDOW_DELTA

        window_patient_vitals = _load_window_patient_vitals(db, window_start)
        window_patient_ids = {row.patient_id for row in window_patient_vitals}

        # Keep recent-window stats where available, and fill remaining patients with latest historical vitals.
        fallback_patient_vitals = _load_latest_available_patient_vitals(
            db,
            exclude_patient_ids=window_patient_ids,
        )
        patient_vitals = [*window_patient_vitals, *fallback_patient_vitals]

        alert_counts = _load_alert_counts(db, window_start)

        if patient_vitals:
            db.query(PatientStats).delete()

            for patient_vital in patient_vitals:
                stat = PatientStats(
                    patient_id=patient_vital.patient_id,
                    avg_heart_rate=patient_vital.avg_heart_rate or 0,
                    avg_temperature=patient_vital.avg_temperature or 0,
                    avg_oxygen=patient_vital.avg_oxygen or 0,
                    alerts_count=alert_counts.get(patient_vital.patient_id, 0),
                )

                db.add(stat)

        PatientRepository.generate_post_discharge_summaries(db)
        db.commit()
