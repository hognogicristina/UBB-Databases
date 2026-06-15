from __future__ import annotations

from datetime import timedelta

from app.simulator.buffers.buffers import SimulatorBuffers
from app.simulator.config.simulator_config import SimulatorConfig
from app.simulator.messaging.kafka_producer import SimulatorKafkaProducer
from app.simulator.repositories.simulator_repository import SimulatorRepository
from app.utils.datetime import now_utc


class BatchService:
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

    def run_batch_analytics_job(self) -> None:
        now = now_utc()
        window_start = now - timedelta(seconds=self.config.batch_interval_seconds)
        recent_vitals, recent_alerts = self.buffers.snapshot_recent_samples(window_start)

        avg_hr = 0.0
        avg_spo2 = 0.0
        avg_temp = 0.0

        if recent_vitals:
            avg_hr = sum(sample["heart_rate"] for sample in recent_vitals) / len(recent_vitals)
            avg_spo2 = sum(sample["oxygen_saturation"] for sample in recent_vitals) / len(recent_vitals)
            avg_temp = sum(sample["temperature"] for sample in recent_vitals) / len(recent_vitals)

        patient_ids = {
            sample["patient_id"]
            for sample in recent_vitals
            if sample.get("patient_id") is not None
        }
        patient_ids.update(
            sample["patient_id"]
            for sample in recent_alerts
            if sample.get("patient_id") is not None
        )

        payload = {
            "event": "batch",
            "timestamp": now.isoformat(),
            "avg_heart_rate": round(avg_hr, 2),
            "avg_oxygen": round(avg_spo2, 2),
            "avg_temperature": round(avg_temp, 2),
            "alerts_count": len(recent_alerts),
            "patients_count": len(patient_ids),
        }

        self.producer.send_batch(payload)
