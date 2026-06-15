import json
import time
import asyncio
import traceback
from datetime import datetime
from types import SimpleNamespace

from confluent_kafka import Consumer

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.patient.patient import Patient
from app.models.vital import Vital
from app.service.metrics import streaming_metrics_store
from app.utils.datetime import now_utc, to_utc
from app.websocket.manager import manager

VITAL_ALLOWED_FIELDS = {
    "patient_id",
    "heart_rate",
    "oxygen_saturation",
    "temperature",
    "systolic_bp",
    "diastolic_bp",
    "recorded_at",
}


def build_consumer():
    return Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": "medstream-vitals-consumer",
            "auto.offset.reset": "earliest",
        }
    )


def schedule_broadcast(app_loop: asyncio.AbstractEventLoop, message: dict):
    future = asyncio.run_coroutine_threadsafe(manager.broadcast(message), app_loop)
    future.add_done_callback(lambda f: f.exception())


def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None

    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def handle_vital_event(payload: dict, app_loop: asyncio.AbstractEventLoop):
    clean_payload = {k: v for k, v in payload.items() if k in VITAL_ALLOWED_FIELDS}

    parsed_recorded_at = parse_datetime(clean_payload.get("recorded_at"))
    if parsed_recorded_at is not None:
        clean_payload["recorded_at"] = parsed_recorded_at
    else:
        clean_payload.pop("recorded_at", None)

    with SessionLocal() as db:
        patient_id = clean_payload.get("patient_id")
        if patient_id is None:
            print("Skipping vital event: missing patient_id")
            return

        patient = db.get(Patient, patient_id)
        if patient is None:
            print(f"Skipping vital event: patient {patient_id} does not exist")
            return
        if patient.is_discharged:
            print(f"Skipping vital event: patient {patient_id} is discharged")
            return

        vital = Vital(**clean_payload)
        db.add(vital)
        db.commit()
        db.refresh(vital)

        streaming_metrics_store.record_vital(vital, 0)

        schedule_broadcast(
            app_loop,
            {
                "type": "vital",
                "data": {
                    "patient_id": vital.patient_id,
                    "heart_rate": vital.heart_rate,
                    "oxygen_saturation": vital.oxygen_saturation,
                    "temperature": vital.temperature,
                    "systolic_bp": vital.systolic_bp,
                    "diastolic_bp": vital.diastolic_bp,
                    "recorded_at": to_utc(vital.recorded_at).isoformat(),
                },
            },
        )


def handle_alert_event(payload: dict, app_loop: asyncio.AbstractEventLoop):
    if payload.get("event") == "discharge":
        discharge_created_at_dt = parse_datetime(payload.get("created_at"))
        discharge_created_at_iso = (
            to_utc(discharge_created_at_dt).isoformat() if discharge_created_at_dt is not None else payload.get("created_at")
        )
        discharge_event = {
            "patient_id": payload.get("patient_id"),
            "reason": payload.get("reason"),
            "note": payload.get("note"),
            "trigger": payload.get("trigger"),
            "treatment_count": payload.get("treatment_count"),
            "alert_count": payload.get("alert_count"),
            "created_at": discharge_created_at_iso,
        }
        if discharge_event["patient_id"] is None:
            print("Skipping discharge event: missing patient_id")
            return

        schedule_broadcast(
            app_loop,
            {
                "type": "discharge",
                "data": discharge_event,
            },
        )
        return

    if payload.get("event") == "transfer":
        transfer_created_at_dt = parse_datetime(payload.get("created_at"))
        transfer_created_at_iso = (
            to_utc(transfer_created_at_dt).isoformat() if transfer_created_at_dt is not None else payload.get("created_at")
        )
        transfer_event = {
            "patient_id": payload.get("patient_id"),
            "reason": payload.get("reason"),
            "trigger": payload.get("trigger"),
            "alert_count": payload.get("alert_count"),
            "treatment_count": payload.get("treatment_count"),
            "created_at": transfer_created_at_iso,
        }
        if transfer_event["patient_id"] is None:
            print("Skipping transfer event: missing patient_id")
            return

        schedule_broadcast(
            app_loop,
            {
                "type": "transfer",
                "data": transfer_event,
            },
        )
        return

    alert_type = payload.get("alert_type")
    if alert_type is None:
        alert_type = payload.get("type")

    created_at_dt = parse_datetime(payload.get("created_at"))
    created_at_iso = to_utc(created_at_dt).isoformat() if created_at_dt is not None else payload.get("created_at")

    alert_event = {
        "id": payload.get("id"),
        "patient_id": payload.get("patient_id"),
        "vital_id": payload.get("vital_id"),
        "alert_type": alert_type,
        "severity": payload.get("severity"),
        "message": payload.get("message"),
        "created_at": created_at_iso,
    }

    if alert_event["patient_id"] is None:
        print("Skipping alert event: missing patient_id")
        return

    with SessionLocal() as db:
        patient = db.get(Patient, alert_event["patient_id"])
        if patient is None:
            print(f"Skipping alert event: patient {alert_event['patient_id']} does not exist")
            return
        if patient.is_discharged:
            print(f"Skipping alert event broadcast: patient {alert_event['patient_id']} is discharged")
            return

    streaming_metrics_store.record_alert(
        SimpleNamespace(
            id=alert_event["id"],
            patient_id=alert_event["patient_id"],
            vital_id=alert_event["vital_id"],
            alert_type=alert_event["alert_type"],
            severity=alert_event["severity"],
            message=alert_event["message"],
            created_at=created_at_dt or now_utc(),
        )
    )

    schedule_broadcast(
        app_loop,
        {
            "type": "alert",
            "data": alert_event,
        },
    )


def run(app_loop: asyncio.AbstractEventLoop):
    while True:
        consumer = None
        while True:
            try:
                consumer = build_consumer()
                consumer.subscribe([settings.kafka_vitals_topic, settings.kafka_alerts_topic])

                while True:
                    try:
                        message = consumer.poll(1.0)

                        if message is None:
                            continue

                        if message.error():
                            print("Consumer error:", message.error())
                            raise RuntimeError(str(message.error()))

                        payload = json.loads(message.value().decode("utf-8"))
                        payload = payload.get("data", payload)
                        topic = message.topic()

                        if topic == settings.kafka_vitals_topic:
                            handle_vital_event(payload, app_loop)
                            continue
                        if topic == settings.kafka_alerts_topic:
                            handle_alert_event(payload, app_loop)
                            continue

                        print(f"Skipping event from unsupported topic: {topic}")
                    except Exception:
                        traceback.print_exc()
                        raise
            except Exception as e:
                print("Consumer reconnecting after error:", e)
                time.sleep(5)
            finally:
                if consumer is not None:
                    consumer.close()
            break


if __name__ == "__main__":
    raise SystemExit("Run consumer via FastAPI startup lifecycle.")
