from __future__ import annotations

from app.core.errors import ValidationError


def strip_string(value: str | None) -> str:
    return str(value or "").strip()


def require_non_empty(value: str | None, field_label: str) -> str:
    trimmed = strip_string(value)
    if not trimmed:
        raise ValidationError("REQUIRED_FIELD", context={"field": field_label})
    return trimmed


def validate_text_length(value: str, field_label: str, max_length: int) -> str:
    if len(value) > max_length:
        raise ValidationError("FIELD_TOO_LONG", context={"field": field_label, "max": max_length})
    return value


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = strip_string(value)
    return trimmed or None


def validate_non_empty_update(updated: bool, message: str) -> None:
    if not updated:
        raise ValidationError("NO_UPDATES_PROVIDED", context={"message": message})


def validate_list_not_empty(value: list, field_label: str) -> list:
    if not value:
        raise ValidationError("AT_LEAST_ONE_REQUIRED", context={"field": field_label})
    return value
