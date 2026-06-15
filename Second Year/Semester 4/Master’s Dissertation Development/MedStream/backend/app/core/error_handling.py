from __future__ import annotations

from fastapi import HTTPException

from app.core.error_messages import resolve_error_message
from app.core.errors import AppError


def raise_http_from_error(error: Exception):
    if isinstance(error, HTTPException):
        raise error

    if isinstance(error, AppError):
        raise HTTPException(
            status_code=error.status_code,
            detail=resolve_error_message(error.code, error.context),
        ) from error

    raise error
