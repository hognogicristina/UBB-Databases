from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from app.core.config import settings
from app.core.errors import AuthorizationError
from app.repositories.auth_repository import (
    TOKEN_TTL,
    create_email_verification_token,
    create_password_reset_token,
    hash_token,
)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    try:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)
    except Exception as error:
        raise AuthorizationError("INVALID_TOKEN") from error


def _sign(payload_segment: str) -> str:
    secret = settings.auth_secret_key.encode("utf-8")
    signature = hmac.new(secret, payload_segment.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(signature)


def create_access_token(doctor_id: int) -> str:
    expires_at = int(time.time()) + settings.auth_token_ttl_minutes * 60
    payload = {
        "sub": "doctor",
        "doctor_id": doctor_id,
        "exp": expires_at,
    }
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature_segment = _sign(payload_segment)
    return f"doctor.{payload_segment}.{signature_segment}"


def parse_access_token(token: str) -> int:
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "doctor":
        raise AuthorizationError("INVALID_TOKEN")

    _, payload_segment, signature_segment = parts
    expected_signature = _sign(payload_segment)
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise AuthorizationError("INVALID_TOKEN")

    try:
        payload = json.loads(_b64url_decode(payload_segment).decode("utf-8"))
    except Exception as error:
        raise AuthorizationError("INVALID_TOKEN") from error

    if payload.get("sub") != "doctor":
        raise AuthorizationError("INVALID_TOKEN")

    doctor_id = payload.get("doctor_id")
    expires_at = payload.get("exp")
    if not isinstance(doctor_id, int) or not isinstance(expires_at, int):
        raise AuthorizationError("INVALID_TOKEN")

    if int(time.time()) >= expires_at:
        raise AuthorizationError("TOKEN_EXPIRED")

    return doctor_id


__all__ = [
    "TOKEN_TTL",
    "create_email_verification_token",
    "create_password_reset_token",
    "hash_token",
    "create_access_token",
    "parse_access_token",
]
