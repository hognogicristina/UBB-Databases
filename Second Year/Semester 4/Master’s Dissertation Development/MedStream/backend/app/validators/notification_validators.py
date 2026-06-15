from __future__ import annotations

from app.validators.auth_validators import validate_email_address
from app.validators.common_validators import require_non_empty


def validate_notification_recipient(value: str | None) -> str:
    return validate_email_address(value)


def validate_notification_subject(value: str | None) -> str:
    return require_non_empty(value, "Subject")


def validate_notification_body(value: str | None, field_label: str) -> str:
    return require_non_empty(value, field_label)


def validate_smtp_host(value: str | None) -> str:
    return require_non_empty(value, "SMTP host")
