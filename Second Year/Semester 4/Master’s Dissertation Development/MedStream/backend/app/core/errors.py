from __future__ import annotations


class AppError(Exception):
    def __init__(self, code: str, *, status_code: int = 400, context: dict | None = None):
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.context = context or {}


class ValidationError(AppError):
    def __init__(self, code: str, *, context: dict | None = None):
        super().__init__(code, status_code=400, context=context)


class ConflictError(AppError):
    def __init__(self, code: str, *, context: dict | None = None):
        super().__init__(code, status_code=400, context=context)


class AuthorizationError(AppError):
    def __init__(self, code: str, *, context: dict | None = None):
        super().__init__(code, status_code=401, context=context)


class PermissionDeniedError(AppError):
    def __init__(self, code: str, *, context: dict | None = None):
        super().__init__(code, status_code=403, context=context)


class NotFoundError(AppError):
    def __init__(self, code: str, *, context: dict | None = None):
        super().__init__(code, status_code=404, context=context)
