from __future__ import annotations

from dataclasses import dataclass

BATCH_INTERVAL_SECONDS = 30


@dataclass(frozen=True)
class SimulatorConfig:
    batch_interval_seconds: int
    max_streamed_patients: int = 50
    vital_sample_rate: float = 0.02
    always_stream_alerts: bool = True
    cycle_sleep_seconds: int = 2
    patient_spawn_probability: float = 0.8
    random_discharge_probability: float = 0.005
    base_random_activity_probability: float = 0.005
    patient_activity_limit_range: tuple[int, int] = (3, 5)
    patient_activity_cooldown_range_minutes: tuple[int, int] = (30, 60)
    random_activity_state_multiplier: dict[str, float] | None = None

    @classmethod
    def from_env(cls) -> "SimulatorConfig":
        return cls(
            batch_interval_seconds=BATCH_INTERVAL_SECONDS,
            random_activity_state_multiplier={
                "stable": 0.05,
                "recovering": 0.1,
                "monitoring": 0.2,
                "warning": 0.7,
                "critical": 1.0,
            },
        )
