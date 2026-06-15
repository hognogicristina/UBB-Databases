from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import NotFoundError, ValidationError
from passlib.context import CryptContext
from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.api.activity_utils import (
    attach_activity_relationships,
    ensure_activity_departments_match,
    ensure_activity_modifier,
    ensure_activity_patients_are_editable,
    ensure_activity_patients_match_doctor_department,
    ensure_supported_activity_type,
    load_activity_or_404,
    load_doctors_for_activity,
    load_patients_for_activity,
)
from app.db.session import SessionLocal
from app.models.doctor.doctor import Doctor
from app.models.doctor.doctor_activity import DoctorActivity
from app.models.doctor.doctor_account_recovery import DoctorAccountRecovery
from app.models.doctor.doctor_email_verification import DoctorEmailVerification
from app.models.doctor.doctor_password_reset import DoctorPasswordReset
from app.models.patient import Patient
from app.repositories.auth_repository import (
    TOKEN_TTL,
    create_account_recovery_token,
    create_email_verification_token,
    create_password_reset_token,
    hash_token,
)
from app.repositories.notification_repository import (
    send_account_recovery_email,
    send_email_change_verification_email,
    send_password_reset_email,
    send_registration_verification_email,
)
from app.service.auth_tokens import create_access_token
from app.utils.datetime import now_utc, to_utc
from app.validators.doctor_validators import (
    AuthorizationError,
    validate_activity_description,
    validate_activity_title,
    validate_activity_type,
    parse_doctor_token,
    validate_activity_payload,
    validate_activity_creation,
    validate_activity_status,
    validate_authorization_header,
    validate_doctor_create_payload,
    validate_doctor_email,
    validate_doctor_identifier_match,
    validate_doctor_patient_department_match,
    validate_doctor_has_no_incoming_activities,
    validate_doctor_self_action,
    validate_doctor_status,
    validate_doctor_uniqueness,
    validate_doctor_update_payload,
    validate_identifier_payload,
    validate_login_payload,
    validate_password_reset_payload,
)
from app.validators.patient_validators import phone_uniqueness_values, validate_patient_assignment

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class DoctorRepository:
    def get_email_verification_expired(self, doctor_id: int) -> bool:
        with SessionLocal() as db:
            verification = db.execute(
                select(DoctorEmailVerification)
                .where(DoctorEmailVerification.doctor_id == doctor_id)
                .order_by(DoctorEmailVerification.created_at.desc(), DoctorEmailVerification.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            if verification is None:
                return False
            return to_utc(verification.expires_at) < now_utc()

    def list_doctors(self):
        with SessionLocal() as db:
            return db.execute(select(Doctor)).scalars().all()

    def get_current_doctor(self, authorization: str | None):
        token = validate_authorization_header(authorization)
        doctor_id = parse_doctor_token(token)

        with SessionLocal() as db:
            doctor = db.get(Doctor, doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")
            validate_doctor_status(doctor.is_active)
            return doctor

    def get_doctor_activities(self, doctor_id: int):
        with SessionLocal() as db:
            doctor = db.get(Doctor, doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            status_priority = case(
                (DoctorActivity.status == "incoming", 1),
                (DoctorActivity.status == "completed", 2),
                (DoctorActivity.status == "canceled", 3),
                else_=4,
            )
            incoming_sort = case(
                (DoctorActivity.status == "incoming", func.coalesce(DoctorActivity.scheduled_at, DoctorActivity.created_at)),
                else_=None,
            )
            completed_sort = case(
                (DoctorActivity.status == "completed", DoctorActivity.created_at),
                else_=None,
            )
            canceled_sort = case(
                (DoctorActivity.status == "canceled", DoctorActivity.created_at),
                else_=None,
            )

            return db.execute(
                select(DoctorActivity)
                .options(selectinload(DoctorActivity.patients), selectinload(DoctorActivity.doctors))
                .where(DoctorActivity.doctor_id == doctor_id)
                .order_by(
                    status_priority.asc(),
                    incoming_sort.asc(),
                    completed_sort.desc(),
                    canceled_sort.desc(),
                    DoctorActivity.id.asc(),
                )
            ).scalars().all()

    def create_doctor_activity(self, doctor_id: int, payload, current_doctor_id: int):
        with SessionLocal() as db:
            validate_doctor_self_action(current_doctor_id, doctor_id, "create activities")

            doctor = db.get(Doctor, doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            normalized_type, normalized_title, normalized_description, payload_doctor_ids = validate_activity_payload(
                payload.type,
                payload.title,
                payload.description,
                payload.doctor_ids,
            )

            ensure_supported_activity_type(normalized_type)
            patients = load_patients_for_activity(db, payload.patient_ids)
            for patient in patients:
                validate_patient_assignment(db, current_doctor_id, patient.id)
            ensure_activity_patients_match_doctor_department(patients, doctor)
            ensure_activity_patients_are_editable(patients)

            doctor_ids = payload_doctor_ids
            if current_doctor_id not in doctor_ids:
                doctor_ids = [current_doctor_id, *doctor_ids]
            doctors = load_doctors_for_activity(db, doctor_ids)
            ensure_activity_departments_match(patients, doctors)
            for activity_doctor in doctors:
                for patient in patients:
                    validate_activity_creation(db, activity_doctor, patient)

            activity = DoctorActivity(
                doctor_id=doctor_id,
                patient_id=patients[0].id,
                type=normalized_type,
                title=normalized_title,
                description=normalized_description,
                scheduled_at=payload.scheduled_at,
                status="incoming",
            )
            attach_activity_relationships(activity, patients, doctors)

            db.add(activity)
            db.commit()
            return load_activity_or_404(db, activity.id)

    def update_doctor_activity(self, doctor_id: int, activity_id: int, payload, current_doctor_id: int):
        with SessionLocal() as db:
            validate_doctor_self_action(current_doctor_id, doctor_id, "update activities")

            activity = load_activity_or_404(db, activity_id)

            if activity.doctor_id != doctor_id:
                raise NotFoundError("ACTIVITY_NOT_FOUND")

            ensure_activity_modifier(activity, doctor_id)
            if activity.status == "completed":
                raise ValidationError("COMPLETED_ACTIVITY_EDIT_FORBIDDEN")

            updated_fields = []

            if payload.type is not None:
                normalized_type = validate_activity_type(payload.type)
                ensure_supported_activity_type(normalized_type)
                activity.type = normalized_type
                updated_fields.append("type")

            if payload.title is not None:
                activity.title = validate_activity_title(payload.title)
                updated_fields.append("title")

            if payload.description is not None:
                activity.description = validate_activity_description(payload.description)
                updated_fields.append("description")

            if payload.scheduled_at is not None:
                activity.scheduled_at = payload.scheduled_at
                updated_fields.append("scheduled_at")

            if payload.status is not None:
                activity.status = validate_activity_status(payload.status)
                updated_fields.append("status")

            patients = list(activity.patients)
            ensure_activity_patients_are_editable(patients)

            if payload.doctor_ids is not None:
                doctor_ids = payload.doctor_ids
                if current_doctor_id not in doctor_ids:
                    doctor_ids = [current_doctor_id, *doctor_ids]
                doctors = load_doctors_for_activity(db, doctor_ids)
                ensure_activity_departments_match(patients, doctors)
                attach_activity_relationships(activity, patients, doctors)
                updated_fields.append("doctor_ids")

            db.commit()

            activity = load_activity_or_404(db, activity.id)

            return activity, updated_fields

    def update_current_doctor(self, doctor_id: int, payload):
        with SessionLocal() as db:
            doctor = db.execute(
                select(Doctor)
                .options(selectinload(Doctor.patients))
                .where(Doctor.id == doctor_id)
            ).scalar_one_or_none()
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            updates = validate_doctor_update_payload(payload)
            validate_doctor_uniqueness(
                db,
                Doctor,
                phone_number=updates.get("phone_number"),
                license_number=updates.get("license_number"),
                doctor_id=doctor.id,
            )
            requested_specialization = updates.get("specialization")
            if requested_specialization is not None and requested_specialization != doctor.specialization:
                validate_doctor_has_no_incoming_activities(db, doctor.id)
                if any(not patient.is_discharged for patient in doctor.patients):
                    raise ValidationError("DOCTOR_HAS_ADMITTED_ASSIGNED_PATIENTS")

                replacement_doctor = db.execute(
                    select(Doctor)
                    .options(selectinload(Doctor.patients))
                    .where(
                        Doctor.is_active.is_(True),
                        Doctor.specialization == doctor.specialization,
                        Doctor.id != doctor.id,
                    )
                    .order_by(Doctor.last_name.asc(), Doctor.first_name.asc(), Doctor.id.asc())
                ).scalar_one_or_none()
                if replacement_doctor is None:
                    raise ValidationError("SPECIALIZATION_CHANGE_REQUIRES_CURRENT_DEPARTMENT_REPLACEMENT")

                for patient in list(doctor.patients):
                    if not any(existing.id == patient.id for existing in replacement_doctor.patients):
                        replacement_doctor.patients.append(patient)
                    doctor.patients.remove(patient)

            for field, value in updates.items():
                setattr(doctor, field, value)

            try:
                db.commit()
                db.refresh(doctor)
            except IntegrityError as error:
                db.rollback()
                raise ValidationError("DOCTOR_PROFILE_DUPLICATE_FIELDS") from error

            return doctor

    def update_current_doctor_email(self, doctor_id: int, email: str):
        with SessionLocal() as db:
            doctor = db.get(Doctor, doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            normalized_email = validate_doctor_email(email)
            validate_doctor_uniqueness(db, Doctor, email=normalized_email, doctor_id=doctor.id)

            if normalized_email == doctor.email and not doctor.pending_email:
                return doctor, None

            doctor.pending_email = normalized_email
            doctor.email_confirmed = False
            db.commit()
            db.refresh(doctor)
            raw_token, _ = create_email_verification_token(db, doctor, normalized_email)
            db.refresh(doctor)
            return doctor, raw_token

    def request_password_reset(self, payload):
        identifier = validate_identifier_payload(payload)
        with SessionLocal() as db:
            doctors = db.execute(select(Doctor)).scalars().all()
            doctor = next(
                (
                    item
                    for item in doctors
                    if validate_doctor_identifier_match(item.email, item.phone_number, identifier)
                ),
                None,
            )
            expires_at = now_utc() + TOKEN_TTL

            if doctor is not None:
                raw_token, reset = create_password_reset_token(db, doctor)
                expires_at = reset.expires_at
                send_password_reset_email(doctor.email, doctor.first_name, raw_token)

            return expires_at

    def request_account_recovery(self, payload):
        identifier = validate_identifier_payload(payload)
        with SessionLocal() as db:
            doctors = db.execute(select(Doctor)).scalars().all()
            doctor = next(
                (
                    item
                    for item in doctors
                    if validate_doctor_identifier_match(item.email, item.phone_number, identifier)
                ),
                None,
            )
            expires_at = now_utc() + TOKEN_TTL

            if doctor is None:
                return expires_at

            raw_token, recovery = create_account_recovery_token(db, doctor)
            send_account_recovery_email(doctor.email, doctor.first_name, raw_token)
            return recovery.expires_at

    def verify_account_recovery(self, token: str) -> None:
        with SessionLocal() as db:
            if not token:
                raise ValidationError("INVALID_OR_EXPIRED_RESET_TOKEN")

            recovery = db.execute(
                select(DoctorAccountRecovery).where(
                    DoctorAccountRecovery.token_hash == hash_token(token),
                    DoctorAccountRecovery.used_at.is_(None),
                )
            ).scalar_one_or_none()

            if recovery is None or to_utc(recovery.expires_at) < now_utc():
                raise ValidationError("INVALID_OR_EXPIRED_RESET_TOKEN")

            doctor = db.get(Doctor, recovery.doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            if not doctor.is_active:
                doctor.is_active = True
                doctor.deleted_at = None

            recovery.used_at = now_utc()
            db.commit()

    def confirm_password_reset(self, payload):
        token, new_password = validate_password_reset_payload(payload)
        with SessionLocal() as db:
            now = now_utc()
            reset = db.execute(
                select(DoctorPasswordReset).where(
                    DoctorPasswordReset.token_hash == hash_token(token),
                    DoctorPasswordReset.used_at.is_(None),
                )
            ).scalar_one_or_none()

            if reset is None or to_utc(reset.expires_at) < now:
                raise ValidationError("INVALID_OR_EXPIRED_RESET_TOKEN")

            doctor = db.get(Doctor, reset.doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            doctor.password_hash = pwd_context.hash(new_password)
            reset.used_at = to_utc(now)
            db.commit()

    def get_doctor_patients(self, doctor_id: int):
        with SessionLocal() as db:
            doctor = db.execute(
                select(Doctor)
                .options(selectinload(Doctor.patients).joinedload(Patient.address))
                .where(Doctor.id == doctor_id)
            ).scalar_one_or_none()
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")
            return sorted(doctor.patients, key=lambda patient: patient.id, reverse=True)

    def get_available_doctors_by_department(self, department: str, exclude_doctor_id: int):
        with SessionLocal() as db:
            doctors = db.execute(
                select(Doctor)
                .where(
                    Doctor.is_active.is_(True),
                    Doctor.specialization == department,
                    Doctor.id != exclude_doctor_id,
                )
                .order_by(Doctor.last_name.asc(), Doctor.first_name.asc(), Doctor.id.asc())
            ).scalars().all()
            return doctors

    def delete_doctor(self, doctor_id: int, current_doctor_id: int):
        with SessionLocal() as db:
            validate_doctor_self_action(current_doctor_id, doctor_id, "delete account")
            validate_doctor_has_no_incoming_activities(db, doctor_id)
            doctor = db.execute(
                select(Doctor)
                .options(selectinload(Doctor.patients).joinedload(Patient.address))
                .where(Doctor.id == doctor_id)
            ).scalar_one_or_none()
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            replacement_doctor = db.execute(
                select(Doctor)
                .where(
                    Doctor.is_active.is_(True),
                    Doctor.specialization == doctor.specialization,
                    Doctor.id != doctor.id,
                )
                .order_by(Doctor.license_number.asc(), Doctor.id.asc())
            ).scalar_one_or_none()
            if replacement_doctor is None:
                raise ValidationError("ONLY_DOCTOR_IN_DEPARTMENT")

            for patient in list(doctor.patients):
                if not any(existing.id == patient.id for existing in replacement_doctor.patients):
                    replacement_doctor.patients.append(patient)

            doctor.patients.clear()

            doctor.is_active = False
            if doctor.deleted_at is None:
                doctor.deleted_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(doctor)
            return doctor

    def assign_patient_to_doctor(self, doctor_id: int, patient_id: int, current_doctor_id: int):
        with SessionLocal() as db:
            validate_doctor_self_action(current_doctor_id, doctor_id, "assign patients")

            doctor = db.execute(
                select(Doctor)
                .options(selectinload(Doctor.patients).joinedload(Patient.address))
                .where(Doctor.id == doctor_id)
            ).scalar_one_or_none()
            patient = db.get(Patient, patient_id)

            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")
            if patient is None:
                raise NotFoundError("PATIENT_NOT_FOUND")
            validate_doctor_patient_department_match(doctor.specialization, patient.department)

            if not any(existing_patient.id == patient.id for existing_patient in doctor.patients):
                doctor.patients.append(patient)
                db.commit()
                doctor = db.execute(
                    select(Doctor)
                    .options(selectinload(Doctor.patients).joinedload(Patient.address))
                    .where(Doctor.id == doctor_id)
                ).scalar_one_or_none()
                if doctor is None:
                    raise NotFoundError("DOCTOR_NOT_FOUND")

            return sorted(doctor.patients, key=lambda assigned_patient: assigned_patient.id, reverse=True)

    def remove_patient_from_doctor(self, doctor_id: int, patient_id: int):
        with SessionLocal() as db:
            validate_doctor_has_no_incoming_activities(db, doctor_id)
            doctor = db.execute(
                select(Doctor)
                .options(selectinload(Doctor.patients).joinedload(Patient.address))
                .where(Doctor.id == doctor_id)
            ).scalar_one_or_none()
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            target_patient = next((patient for patient in doctor.patients if patient.id == patient_id), None)
            if target_patient is not None:
                patient_with_doctors = db.execute(
                    select(Patient)
                    .options(selectinload(Patient.doctors))
                    .where(Patient.id == patient_id)
                ).scalar_one_or_none()
                if patient_with_doctors is None:
                    raise NotFoundError("PATIENT_NOT_FOUND")

                active_assigned_doctors = [item for item in patient_with_doctors.doctors if item.is_active]
                if len(active_assigned_doctors) <= 1:
                    raise ValidationError("LAST_ASSIGNED_DOCTOR_TRANSFER_REQUIRED")

                doctor.patients.remove(target_patient)
                db.commit()
                doctor = db.execute(
                    select(Doctor)
                    .options(selectinload(Doctor.patients).joinedload(Patient.address))
                    .where(Doctor.id == doctor_id)
                ).scalar_one_or_none()
                if doctor is None:
                    raise NotFoundError("DOCTOR_NOT_FOUND")

            patients = sorted(doctor.patients, key=lambda patient: patient.id, reverse=True)
            return patients, bool(target_patient)

    def register_doctor(self, payload):
        validated_payload = validate_doctor_create_payload(payload)

        with SessionLocal() as db:
            duplicate_filters = [Doctor.email == validated_payload["email"], Doctor.license_number == validated_payload["license_number"]]
            phone_values = phone_uniqueness_values(validated_payload["phone_number"])
            if validated_payload["phone_number"]:
                duplicate_filters.append(Doctor.phone_number.in_(phone_values))

            matching_doctors = db.execute(select(Doctor).where(or_(*duplicate_filters))).scalars().all()

            email_match = next((doctor for doctor in matching_doctors if doctor.email == validated_payload["email"]), None)
            phone_match = next((doctor for doctor in matching_doctors if
                                validated_payload["phone_number"] and doctor.phone_number in phone_values), None)
            license_match = next((doctor for doctor in matching_doctors if doctor.license_number == validated_payload["license_number"]),
                                 None)

            if email_match and email_match.is_active:
                if email_match.email_confirmed:
                    raise ValidationError("EMAIL_ALREADY_REGISTERED")
                if phone_match and phone_match.is_active and phone_match.id != email_match.id:
                    raise ValidationError("PHONE_ALREADY_REGISTERED")
                if license_match and license_match.is_active and license_match.id != email_match.id:
                    raise ValidationError("LICENSE_ALREADY_REGISTERED")

                raw_token, _ = create_email_verification_token(db, email_match, email_match.email)
                send_registration_verification_email(email_match.email, email_match.first_name, raw_token)
                return email_match
            if phone_match and phone_match.is_active:
                raise ValidationError("PHONE_ALREADY_REGISTERED")
            if license_match and license_match.is_active:
                raise ValidationError("LICENSE_ALREADY_REGISTERED")

            restore_candidate = next((doctor for doctor in (email_match, phone_match, license_match) if doctor is not None), None)

            if restore_candidate and not restore_candidate.is_active:
                restore_candidate.first_name = validated_payload["first_name"]
                restore_candidate.last_name = validated_payload["last_name"]
                restore_candidate.email = validated_payload["email"]
                restore_candidate.pending_email = None
                restore_candidate.email_confirmed = False
                restore_candidate.phone_number = validated_payload["phone_number"]
                restore_candidate.birth_date = validated_payload["birth_date"]
                restore_candidate.password_hash = pwd_context.hash(validated_payload["password"])
                restore_candidate.specialization = validated_payload["specialization"]
                restore_candidate.license_number = validated_payload["license_number"]
                restore_candidate.is_active = True
                restore_candidate.deleted_at = None
                db.commit()
                db.refresh(restore_candidate)
                raw_token, _ = create_email_verification_token(db, restore_candidate, restore_candidate.email)
                send_registration_verification_email(restore_candidate.email, restore_candidate.first_name, raw_token)
                return restore_candidate

            doctor = Doctor(
                first_name=validated_payload["first_name"],
                last_name=validated_payload["last_name"],
                email=validated_payload["email"],
                pending_email=None,
                email_confirmed=False,
                phone_number=validated_payload["phone_number"],
                birth_date=validated_payload["birth_date"],
                password_hash=pwd_context.hash(validated_payload["password"]),
                specialization=validated_payload["specialization"],
                license_number=validated_payload["license_number"],
            )
            db.add(doctor)
            try:
                db.commit()
                db.refresh(doctor)
            except IntegrityError as error:
                db.rollback()
                raise ValidationError("DOCTOR_IDENTITY_FIELDS_UNIQUE") from error

            raw_token, _ = create_email_verification_token(db, doctor, doctor.email)
            send_registration_verification_email(doctor.email, doctor.first_name, raw_token)
            return doctor

    def login_doctor(self, payload):
        identifier, password = validate_login_payload(payload)
        with SessionLocal() as db:
            doctors = db.execute(select(Doctor)).scalars().all()
            doctor = next(
                (
                    item
                    for item in doctors
                    if validate_doctor_identifier_match(item.email, item.phone_number, identifier)
                ),
                None,
            )
            if not doctor or not doctor.is_active or not pwd_context.verify(password, doctor.password_hash):
                raise AuthorizationError("INVALID_CREDENTIALS")
            return create_access_token(doctor.id)

    def verify_email(self, token: str):
        with SessionLocal() as db:
            if not token:
                raise ValidationError("INVALID_VERIFICATION_TOKEN")

            verification = db.execute(
                select(DoctorEmailVerification).where(DoctorEmailVerification.token_hash == hash_token(token))
            ).scalar_one_or_none()

            if verification is None:
                raise ValidationError("INVALID_VERIFICATION_TOKEN")
            if to_utc(verification.expires_at) < now_utc():
                raise ValidationError("EXPIRED_VERIFICATION_TOKEN")

            doctor = db.get(Doctor, verification.doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            if verification.used_at is not None:
                if doctor.email_confirmed and not doctor.pending_email and verification.target_email == doctor.email:
                    return
                if doctor.pending_email:
                    raise ValidationError("REPLACED_VERIFICATION_TOKEN")
                raise ValidationError("INVALID_VERIFICATION_TOKEN")

            if doctor.pending_email and verification.target_email == doctor.pending_email:
                doctor.email = doctor.pending_email
                doctor.pending_email = None
            elif verification.target_email != doctor.email:
                raise ValidationError("VERIFICATION_TOKEN_EMAIL_MISMATCH")

            doctor.email_confirmed = True
            verification.used_at = now_utc()
            db.commit()

    def resend_verification_email(self, doctor_id: int | None = None, token: str | None = None):
        with SessionLocal() as db:
            resolved_doctor_id = doctor_id
            if resolved_doctor_id is None and token:
                verification = db.execute(
                    select(DoctorEmailVerification).where(DoctorEmailVerification.token_hash == hash_token(token))
                ).scalar_one_or_none()
                if verification is None:
                    raise ValidationError("INVALID_VERIFICATION_TOKEN")
                resolved_doctor_id = verification.doctor_id

            if resolved_doctor_id is None:
                raise ValidationError("INVALID_VERIFICATION_TOKEN")

            doctor = db.get(Doctor, resolved_doctor_id)
            if doctor is None:
                raise NotFoundError("DOCTOR_NOT_FOUND")

            if doctor.email_confirmed and not doctor.pending_email:
                raise ValidationError("EMAIL_ALREADY_VERIFIED")

            target_email = doctor.pending_email or doctor.email
            raw_token, _ = create_email_verification_token(db, doctor, target_email)

            if doctor.pending_email:
                send_email_change_verification_email(target_email, doctor.first_name, raw_token)
            else:
                send_registration_verification_email(target_email, doctor.first_name, raw_token)
