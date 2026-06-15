from __future__ import annotations

from app.core.errors import ValidationError
from app.validators.common_validators import normalize_optional_text, require_non_empty, validate_text_length

ROMANIA_COUNTRY = "Romania"


def validate_required_address_text(value: str | None, field_label: str, max_length: int) -> str:
    text = require_non_empty(value, field_label)
    return validate_text_length(text, field_label, max_length)


def validate_optional_address_text(value: str | None, field_label: str, max_length: int) -> str | None:
    text = normalize_optional_text(value)
    if text is None:
        return None
    return validate_text_length(text, field_label, max_length)


def normalize_postal_code(value: str | None) -> str:
    digits = "".join(char for char in str(value or "").strip() if char.isdigit())
    return digits


def validate_postal_code(value: str | None) -> str:
    digits = normalize_postal_code(value)
    if not digits:
        raise ValidationError("POSTAL_CODE_REQUIRED")
    if len(digits) != 6:
        raise ValidationError("POSTAL_CODE_INVALID_LENGTH")
    return digits


def validate_required_address_fields(address: dict | None) -> dict:
    if address is None:
        raise ValidationError("ADDRESS_REQUIRED")

    return {
        "street": validate_required_address_text(address.get("street"), "Address street", 120),
        "number": validate_required_address_text(address.get("number"), "Address number", 30),
        "city": validate_required_address_text(address.get("city"), "Address city", 100),
        "county": validate_required_address_text(address.get("county"), "Address county", 100),
        "postal_code": validate_postal_code(address.get("postal_code")),
        "apartment": validate_optional_address_text(address.get("apartment"), "Address apartment", 30),
        "country": validate_required_address_text(address.get("country") or ROMANIA_COUNTRY, "Address country", 100),
    }


def validate_address_completeness(address: dict | None) -> bool:
    if address is None:
        return False

    required_keys = ("street", "number", "city", "county", "postal_code")
    provided = {key: address.get(key) for key in required_keys}

    if any(value is not None for value in provided.values()) and not all(value is not None for value in provided.values()):
        raise ValidationError("ADDRESS_FIELDS_INCOMPLETE")

    return all(value is not None for value in provided.values())


def validate_address_create(address: dict | None) -> dict:
    return validate_required_address_fields(address)


def validate_address_update(address: dict | None) -> dict | None:
    if address is None:
        return None

    has_complete_required_fields = validate_address_completeness(address)
    apartment = normalize_optional_text(address.get("apartment"))

    if not has_complete_required_fields and apartment is None:
        return None

    if not has_complete_required_fields and apartment is not None:
        raise ValidationError("ADDRESS_FIELDS_INCOMPLETE")

    return validate_required_address_fields(address)
