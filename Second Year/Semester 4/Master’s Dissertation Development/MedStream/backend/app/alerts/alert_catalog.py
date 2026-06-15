from __future__ import annotations

from typing import Final

CANONICAL_ALERT_TYPES: Final[set[str]] = {
    "heart_rate_high",
    "heart_rate_critical",
    "heart_rate_normalized",
    "oxygen_low",
    "oxygen_critical",
    "oxygen_normalized",
    "temperature_high",
    "temperature_critical",
    "temperature_normalized",
}

LEGACY_ALERT_TYPE_ALIASES: Final[dict[str, str]] = {
    "heart_rate": "heart_rate_high",
    "oxygen": "oxygen_low",
    "oxygen_saturation": "oxygen_low",
    "temperature": "temperature_high",
    "status": "heart_rate_normalized",
    "normal vitals": "heart_rate_normalized",
}


def normalize_alert_type(alert_type: str | None, severity: str | None = None) -> str:
    normalized = str(alert_type or "").strip().lower()
    normalized_severity = str(severity or "").strip().lower()

    if normalized in CANONICAL_ALERT_TYPES:
        return normalized

    if normalized == "heart_rate":
        if normalized_severity == "critical":
            return "heart_rate_critical"
        return "heart_rate_high"

    if normalized in {"oxygen", "oxygen_saturation"}:
        if normalized_severity == "critical":
            return "oxygen_critical"
        return "oxygen_low"

    if normalized == "temperature":
        if normalized_severity == "critical":
            return "temperature_critical"
        return "temperature_high"

    if normalized in LEGACY_ALERT_TYPE_ALIASES:
        return LEGACY_ALERT_TYPE_ALIASES[normalized]

    return normalized


def vital_for_alert_type(alert_type: str) -> str | None:
    if alert_type.startswith("heart_rate_"):
        return "heart_rate"
    if alert_type.startswith("oxygen_"):
        return "oxygen"
    if alert_type.startswith("temperature_"):
        return "temperature"
    return None
