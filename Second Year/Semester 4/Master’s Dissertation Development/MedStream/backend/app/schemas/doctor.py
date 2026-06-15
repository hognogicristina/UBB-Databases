from datetime import date, datetime

from pydantic import BaseModel, Field

PASSWORD_MAX_LENGTH = 72


class DoctorCreate(BaseModel):
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str = Field(max_length=255)
    phone_number: str | None = None
    birth_date: date | None = None
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    confirm_password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    specialization: str
    license_number: str = Field(max_length=50)


class DoctorRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    pending_email: str | None = None
    email_confirmed: bool = True
    email_verification_expired: bool = False
    email_verified: bool = True
    phone_number: str | None
    birth_date: date | None = None
    specialization: str
    license_number: str
    is_active: bool
    deleted_at: datetime | None

    model_config = {"from_attributes": True}


class DoctorUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    specialization: str | None = None
    license_number: str | None = Field(default=None, max_length=50)
    phone_number: str | None = None
    birth_date: date | None = None


class DoctorEmailUpdate(BaseModel):
    email: str = Field(max_length=255)


class LoginRequest(BaseModel):
    identifier: str
    password: str = Field(max_length=PASSWORD_MAX_LENGTH)


class LoginResponse(BaseModel):
    token: str
    model_config = {"from_attributes": True}


class PasswordResetRequest(BaseModel):
    identifier: str


class PasswordResetRequestResponse(BaseModel):
    message: str
    reset_token: str
    expires_at: datetime


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(max_length=PASSWORD_MAX_LENGTH)
    confirm_password: str | None = Field(default=None, max_length=PASSWORD_MAX_LENGTH)


class PasswordResetConfirmResponse(BaseModel):
    message: str


class AccountRecoveryRequestResponse(BaseModel):
    message: str
    recovery_token: str
    expires_at: datetime


class EmailVerificationResponse(BaseModel):
    message: str
