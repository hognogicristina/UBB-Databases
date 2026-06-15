from __future__ import annotations

from dataclasses import dataclass


NORMAL_STATE = "normal"
CRITICAL_STATE = "critical"

VITAL_HEART_RATE = "heart_rate"
VITAL_OXYGEN = "oxygen"
VITAL_TEMPERATURE = "temperature"


@dataclass(frozen=True)
class TransitionAlert:
    alert_type: str
    severity: str
    message: str
    vital: str
    new_state: str


def classify_heart_rate(value: float) -> str:
    if value > 130:
        return CRITICAL_STATE
    if value > 110:
        return "high"
    return NORMAL_STATE


def classify_oxygen(value: float) -> str:
    if value < 88:
        return CRITICAL_STATE
    if value < 92:
        return "low"
    return NORMAL_STATE


def classify_temperature(value: float) -> str:
    if value > 39:
        return CRITICAL_STATE
    if value > 38:
        return "high"
    return NORMAL_STATE


def classify_vital_states(vitals: dict) -> dict[str, str]:
    return {
        VITAL_HEART_RATE: classify_heart_rate(vitals["heart_rate"]),
        VITAL_OXYGEN: classify_oxygen(vitals["oxygen_saturation"]),
        VITAL_TEMPERATURE: classify_temperature(vitals["temperature"]),
    }


def is_abnormal(state: str) -> bool:
    return state != NORMAL_STATE


def build_transition_alerts(*, previous_states: dict[str, str], current_states: dict[str, str], vitals: dict) -> list[TransitionAlert]:
    alerts: list[TransitionAlert] = []

    for vital_key in (VITAL_HEART_RATE, VITAL_OXYGEN, VITAL_TEMPERATURE):
        previous_state = previous_states.get(vital_key, NORMAL_STATE)
        current_state = current_states.get(vital_key, NORMAL_STATE)

        if previous_state == current_state:
            continue

        if is_abnormal(current_state):
            alert_type = f"{vital_key}_{current_state}"
            severity = "critical" if current_state == CRITICAL_STATE else "high"
            if vital_key == VITAL_HEART_RATE:
                value = vitals["heart_rate"]
                message = f"Heart rate {current_state}: {value} bpm"
            elif vital_key == VITAL_OXYGEN:
                value = vitals["oxygen_saturation"]
                message = f"Oxygen {current_state}: {value}%"
            else:
                value = vitals["temperature"]
                message = f"Temperature {current_state}: {value}°C"

            alerts.append(
                TransitionAlert(
                    alert_type=alert_type,
                    severity=severity,
                    message=message,
                    vital=vital_key,
                    new_state=current_state,
                )
            )
            continue

        if is_abnormal(previous_state) and current_state == NORMAL_STATE:
            alert_type = f"{vital_key}_normalized"
            if vital_key == VITAL_HEART_RATE:
                value = vitals["heart_rate"]
                message = f"Heart rate normalized: {value} bpm"
            elif vital_key == VITAL_OXYGEN:
                value = vitals["oxygen_saturation"]
                message = f"Oxygen normalized: {value}%"
            else:
                value = vitals["temperature"]
                message = f"Temperature normalized: {value}°C"

            alerts.append(
                TransitionAlert(
                    alert_type=alert_type,
                    severity="normal",
                    message=message,
                    vital=vital_key,
                    new_state=current_state,
                )
            )

    return alerts
