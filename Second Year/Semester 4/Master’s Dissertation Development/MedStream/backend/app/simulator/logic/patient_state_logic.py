from __future__ import annotations


def evaluate_patient_state(vitals: dict) -> str:
    heart_rate = vitals["heart_rate"]
    oxygen_saturation = vitals["oxygen_saturation"]
    temperature = vitals["temperature"]

    if oxygen_saturation < 88 or heart_rate > 130 or temperature > 39:
        return "critical"

    if oxygen_saturation < 92 or heart_rate > 110 or temperature > 38:
        return "warning"

    return "stable"


def handle_state_transition(patient_id: int, new_state: str, patient_states: dict[int, str]) -> tuple[str | None, str | None]:
    previous_state = patient_states.get(patient_id)
    if previous_state == new_state:
        return previous_state, None

    patient_states[patient_id] = new_state
    return previous_state, new_state
