from fastapi import APIRouter, Header, Query

from app.api.activity_utils import serialize_activity
from app.core.error_handling import raise_http_from_error
from app.core.http import ApiResponse, success_response
from app.schemas.doctor import (
    AccountRecoveryRequestResponse,
    DoctorCreate,
    DoctorEmailUpdate,
    DoctorRead,
    DoctorUpdate,
    EmailVerificationResponse,
    LoginRequest,
    LoginResponse,
    PasswordResetConfirm,
    PasswordResetConfirmResponse,
    PasswordResetRequest,
    PasswordResetRequestResponse,
)
from app.schemas.doctor_activity import DoctorActivityCreate, DoctorActivityRead, DoctorActivityUpdate
from app.schemas.patient import PatientRead
from app.service.doctor_service import DoctorService
from app.service.notifications import send_email_change_verification_email

router = APIRouter(prefix="/doctors", tags=["doctors"])
auth_router = APIRouter(tags=["auth"])
doctor_service = DoctorService()


def serialize(model, schema, extra: dict | None = None):
    payload = schema.model_validate(model, from_attributes=True).model_dump(mode="json")
    if "email_verified" in payload and hasattr(model, "email_confirmed"):
        payload["email_verified"] = bool(model.email_confirmed)
    if extra:
        payload.update(extra)
    return payload


def serialize_many(models, schema):
    return [serialize(model, schema) for model in models]


def get_current_doctor(authorization: str | None):
    try:
        return doctor_service.get_current_doctor(authorization)
    except Exception as error:
        raise_http_from_error(error)


@router.get("", response_model=ApiResponse[list[DoctorRead]])
def list_doctors():
    try:
        doctors = doctor_service.list_doctors()
        return success_response("Doctors retrieved successfully.", serialize_many(doctors, DoctorRead))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/me", response_model=ApiResponse[DoctorRead])
def read_current_doctor(authorization: str | None = Header(default=None)):
    doctor = get_current_doctor(authorization)
    email_verification_expired = doctor_service.get_email_verification_expired(doctor.id)
    return success_response(
        "Doctor profile retrieved successfully.",
        serialize(doctor, DoctorRead, extra={"email_verification_expired": email_verification_expired}),
    )


@router.get("/{doctor_id}/activities", response_model=ApiResponse[list[DoctorActivityRead]])
def get_doctor_activities(doctor_id: int):
    try:
        activities = doctor_service.get_doctor_activities(doctor_id)
        return success_response(
            "Doctor activities retrieved successfully.",
            [serialize_activity(activity) for activity in activities],
        )
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{doctor_id}/activities", response_model=ApiResponse[DoctorActivityRead])
def create_doctor_activity(doctor_id: int, payload: DoctorActivityCreate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        activity = doctor_service.create_doctor_activity(doctor_id, payload, current_doctor.id)
        return success_response("Doctor activity added successfully.", serialize_activity(activity), status_code=201)
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/{doctor_id}/activities/{activity_id}", response_model=ApiResponse[DoctorActivityRead])
def update_doctor_activity(
        doctor_id: int,
        activity_id: int,
        payload: DoctorActivityUpdate,
        authorization: str | None = Header(default=None),
):
    current_doctor = get_current_doctor(authorization)
    try:
        activity, updated_fields = doctor_service.update_doctor_activity(doctor_id, activity_id, payload, current_doctor.id)
        message = "Doctor activity updated successfully." if not updated_fields else f"Doctor activity updated successfully. Updated: {', '.join(updated_fields)}."
        return success_response(message, serialize_activity(activity))
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/me", response_model=ApiResponse[DoctorRead])
def update_current_doctor(payload: DoctorUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        doctor = doctor_service.update_current_doctor(current_doctor.id, payload)
        return success_response("Doctor profile updated successfully.", serialize(doctor, DoctorRead))
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/me/email", response_model=ApiResponse[DoctorRead])
def update_current_doctor_email(
        payload: DoctorEmailUpdate,
        authorization: str | None = Header(default=None),
):
    current_doctor = get_current_doctor(authorization)
    try:
        doctor, raw_token = doctor_service.update_current_doctor_email(current_doctor.id, payload.email)
        if raw_token is not None:
            send_email_change_verification_email(
                doctor.pending_email,
                doctor.first_name,
                raw_token,
            )
        return success_response("Doctor email update requested successfully.", serialize(doctor, DoctorRead))
    except Exception as error:
        raise_http_from_error(error)


@router.post("/password-reset/request", response_model=ApiResponse[PasswordResetRequestResponse])
def request_password_reset(payload: PasswordResetRequest):
    try:
        expires_at = doctor_service.request_password_reset(payload)
        response = PasswordResetRequestResponse(
            message="If the email exists, password reset instructions were sent successfully.",
            reset_token="",
            expires_at=expires_at,
        )
        return success_response(response.message, response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@router.post("/account-recovery/request", response_model=ApiResponse[AccountRecoveryRequestResponse])
def request_account_recovery(payload: PasswordResetRequest):
    try:
        expires_at = doctor_service.request_account_recovery(payload)
        response = AccountRecoveryRequestResponse(
            message="If the account exists, recovery instructions were sent successfully.",
            recovery_token="",
            expires_at=expires_at,
        )
        return success_response(response.message, response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@auth_router.post("/auth/recover-account", response_model=ApiResponse[AccountRecoveryRequestResponse])
def auth_recover_account(payload: PasswordResetRequest):
    try:
        expires_at = doctor_service.request_account_recovery(payload)
        response = AccountRecoveryRequestResponse(
            message="If the account exists, recovery instructions were sent successfully.",
            recovery_token="",
            expires_at=expires_at,
        )
        return success_response(response.message, response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@auth_router.get("/auth/recover-account/verify", response_model=ApiResponse[EmailVerificationResponse])
def verify_recover_account(token: str | None = Query(default=None)):
    try:
        doctor_service.verify_account_recovery(token or "")
        response = EmailVerificationResponse(message="Account recovered successfully.")
        return success_response(response.message, response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@router.post("/password-reset/confirm", response_model=ApiResponse[PasswordResetConfirmResponse])
def confirm_password_reset(payload: PasswordResetConfirm):
    try:
        doctor_service.confirm_password_reset(payload)
        response = PasswordResetConfirmResponse(message="Password reset successful.")
        return success_response(response.message, response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{doctor_id}/patients", response_model=ApiResponse[list[PatientRead]])
def get_doctor_activity_patients(doctor_id: int):
    try:
        patients = doctor_service.get_doctor_patients(doctor_id)
        return success_response("Doctor patients retrieved successfully.", serialize_many(patients, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/available", response_model=ApiResponse[list[DoctorRead]])
def get_available_doctors(department: str = Query(...), exclude_doctor_id: int = Query(..., ge=1)):
    try:
        doctors = doctor_service.get_available_doctors_by_department(department, exclude_doctor_id)
        return success_response("Available doctors retrieved successfully.", serialize_many(doctors, DoctorRead))
    except Exception as error:
        raise_http_from_error(error)


@router.delete("/{doctor_id}", response_model=ApiResponse[DoctorRead])
def delete_doctor(doctor_id: int, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        doctor = doctor_service.delete_doctor(doctor_id, current_doctor.id)
        return success_response("Doctor account deactivated successfully.", serialize(doctor, DoctorRead))
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{doctor_id}/patients/{patient_id}", response_model=ApiResponse[list[PatientRead]])
def assign_patient_to_doctor(doctor_id: int, patient_id: int, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        patients = doctor_service.assign_patient_to_doctor(doctor_id, patient_id, current_doctor.id)
        return success_response("Patient assigned to doctor successfully.", serialize_many(patients, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.delete("/{doctor_id}/patients/{patient_id}", response_model=ApiResponse[list[PatientRead]])
def remove_patient_from_doctor(doctor_id: int, patient_id: int):
    try:
        patients, removed = doctor_service.remove_patient_from_doctor(doctor_id, patient_id)
        message = "Patient removed from doctor successfully." if removed else "Doctor patients retrieved successfully."
        return success_response(message, serialize_many(patients, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.post("", response_model=ApiResponse[DoctorRead])
def create_doctor(payload: DoctorCreate):
    try:
        doctor = doctor_service.register_doctor(payload)
        return success_response("Doctor account created successfully.", serialize(doctor, DoctorRead), status_code=201)
    except Exception as error:
        raise_http_from_error(error)


@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(payload: LoginRequest):
    try:
        token = doctor_service.login_doctor(payload)
        response = LoginResponse(token=token)
        return success_response("Login successful.", response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@auth_router.post("/login", response_model=ApiResponse[LoginResponse])
def root_login(payload: LoginRequest):
    return login(payload)


@auth_router.post("/register", response_model=ApiResponse[DoctorRead])
def register(payload: DoctorCreate):
    try:
        doctor = doctor_service.register_doctor(payload)
        return success_response("Doctor account created successfully. Please verify your email.", serialize(doctor, DoctorRead),
                                status_code=201)
    except Exception as error:
        raise_http_from_error(error)


@auth_router.get("/auth/verify-email", response_model=ApiResponse[EmailVerificationResponse])
def verify_email(token: str | None = Query(default=None)):
    try:
        doctor_service.verify_email(token)
        response = EmailVerificationResponse(message="Email verified successfully.")
        return success_response(response.message, response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@auth_router.post("/auth/resend-verification", response_model=ApiResponse[EmailVerificationResponse])
def resend_verification_email(
        authorization: str | None = Header(default=None),
        token: str | None = Query(default=None),
):
    try:
        current_doctor = get_current_doctor(authorization) if authorization else None
        doctor_service.resend_verification_email(current_doctor.id if current_doctor else None, token)
        response = EmailVerificationResponse(message="Verification email sent.")
        return success_response(response.message, response.model_dump(mode="json"))
    except Exception as error:
        raise_http_from_error(error)


@auth_router.post("/auth/forgot-password", response_model=ApiResponse[PasswordResetRequestResponse])
def auth_forgot_password(payload: PasswordResetRequest):
    return request_password_reset(payload)


@auth_router.post("/auth/reset-password", response_model=ApiResponse[PasswordResetConfirmResponse])
def auth_reset_password(payload: PasswordResetConfirm):
    return confirm_password_reset(payload)
