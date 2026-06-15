from __future__ import annotations

import random
import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.simulator.config.simulator_config import SimulatorConfig
from app.utils.datetime import now_utc, to_utc


@dataclass
class SimulatorBuffers:
    config: SimulatorConfig
    vitals_buffer: deque = field(default_factory=deque)
    alerts_buffer: deque = field(default_factory=deque)
    lock: threading.Lock = field(default_factory=threading.Lock)
    patient_states: dict[int, str] = field(default_factory=dict)
    patient_last_normal_time: dict[int, datetime] = field(default_factory=dict)
    patient_last_activity_time: dict[int, datetime] = field(default_factory=dict)
    patient_activity_limits: dict[int, int] = field(default_factory=dict)
    patient_activity_cooldowns: dict[int, int] = field(default_factory=dict)
    streamed_patients: set[int] = field(default_factory=set)

    def get_patient_activity_limit(self, patient_id: int) -> int:
        if patient_id not in self.patient_activity_limits:
            self.patient_activity_limits[patient_id] = random.randint(*self.config.patient_activity_limit_range)
        return self.patient_activity_limits[patient_id]

    def get_patient_activity_cooldown_minutes(self, patient_id: int) -> int:
        if patient_id not in self.patient_activity_cooldowns:
            self.patient_activity_cooldowns[patient_id] = random.randint(*self.config.patient_activity_cooldown_range_minutes)
        return self.patient_activity_cooldowns[patient_id]

    def can_create_activity_for_patient(
            self,
            patient_id: int,
            incoming_count: int,
            activities_created_in_cycle: set[int] | None = None,
    ) -> bool:
        if activities_created_in_cycle is not None and patient_id in activities_created_in_cycle:
            return False

        incoming_limit = self.get_patient_activity_limit(patient_id)
        if incoming_count >= incoming_limit:
            return False

        last_created_at = self.patient_last_activity_time.get(patient_id)
        if last_created_at is None:
            return True

        cooldown = timedelta(minutes=self.get_patient_activity_cooldown_minutes(patient_id))
        return now_utc() - to_utc(last_created_at) >= cooldown

    def mark_activity_created(self, patient_id: int, activities_created_in_cycle: set[int] | None = None) -> None:
        self.patient_last_activity_time[patient_id] = now_utc()
        if activities_created_in_cycle is not None:
            activities_created_in_cycle.add(patient_id)

    def append_vital_sample(self, patient_id: int, vitals: dict) -> None:
        with self.lock:
            self.vitals_buffer.append(
                {
                    "timestamp": now_utc(),
                    "patient_id": patient_id,
                    **vitals,
                }
            )

    def append_alert_sample(self, patient_id: int, alert_type: str) -> None:
        with self.lock:
            self.alerts_buffer.append(
                {
                    "timestamp": now_utc(),
                    "patient_id": patient_id,
                    "type": alert_type,
                }
            )

    def snapshot_recent_samples(self, window_start: datetime) -> tuple[list[dict], list[dict]]:
        with self.lock:
            recent_vitals = [v for v in self.vitals_buffer if to_utc(v["timestamp"]) >= window_start]
            recent_alerts = [a for a in self.alerts_buffer if to_utc(a["timestamp"]) >= window_start]

            while self.vitals_buffer and to_utc(self.vitals_buffer[0]["timestamp"]) < window_start:
                self.vitals_buffer.popleft()

            while self.alerts_buffer and to_utc(self.alerts_buffer[0]["timestamp"]) < window_start:
                self.alerts_buffer.popleft()

        return recent_vitals, recent_alerts

    def should_stream_patient_vitals(self, patient_id: int) -> bool:
        if patient_id in self.streamed_patients:
            return True

        if len(self.streamed_patients) < self.config.max_streamed_patients:
            self.streamed_patients.add(patient_id)
            return True

        return random.random() < self.config.vital_sample_rate
