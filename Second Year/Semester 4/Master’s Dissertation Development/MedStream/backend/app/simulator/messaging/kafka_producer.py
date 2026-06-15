from __future__ import annotations

from app.core.config import settings
from app.kafka.producer import send_message


class SimulatorKafkaProducer:
    def send_vital(self, payload: dict) -> None:
        send_message(settings.kafka_vitals_topic, payload)

    def send_alert(self, payload: dict) -> None:
        send_message(settings.kafka_alerts_topic, payload)

    def send_transfer(self, payload: dict) -> None:
        send_message(settings.kafka_alerts_topic, payload)

    def send_discharge(self, payload: dict) -> None:
        send_message(settings.kafka_alerts_topic, payload)

    def send_batch(self, payload: dict) -> None:
        send_message(settings.kafka_batch_topic, payload)
