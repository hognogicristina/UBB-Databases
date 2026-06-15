import hashlib
import secrets
from datetime import timedelta

from sqlalchemy import select

from app.models.doctor.doctor_email_verification import DoctorEmailVerification
from app.models.doctor.doctor_account_recovery import DoctorAccountRecovery
from app.models.doctor.doctor_password_reset import DoctorPasswordReset
from app.utils.datetime import now_utc, to_utc
from app.validators.auth_validators import validate_email_address

TOKEN_TTL = timedelta(minutes=30)


def hash_token(token: str):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(db, doctor):
    now = now_utc()
    active_tokens = db.execute(
        select(DoctorPasswordReset).where(
            DoctorPasswordReset.doctor_id == doctor.id,
            DoctorPasswordReset.used_at.is_(None),
        )
    ).scalars().all()

    for active_token in active_tokens:
        active_token.used_at = to_utc(now)

    raw_token = secrets.token_urlsafe(32)
    reset = DoctorPasswordReset(
        doctor_id=doctor.id,
        token_hash=hash_token(raw_token),
        expires_at=to_utc(now + TOKEN_TTL),
    )
    db.add(reset)
    db.commit()
    db.refresh(reset)
    return raw_token, reset


def create_email_verification_token(db, doctor, target_email: str):
    validated_target_email = validate_email_address(target_email)
    now = now_utc()
    active_tokens = db.execute(
        select(DoctorEmailVerification).where(
            DoctorEmailVerification.doctor_id == doctor.id,
            DoctorEmailVerification.used_at.is_(None),
        )
    ).scalars().all()

    for active_token in active_tokens:
        active_token.used_at = to_utc(now)

    raw_token = secrets.token_urlsafe(32)
    verification = DoctorEmailVerification(
        doctor_id=doctor.id,
        token_hash=hash_token(raw_token),
        target_email=validated_target_email,
        expires_at=to_utc(now + TOKEN_TTL),
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return raw_token, verification


def create_account_recovery_token(db, doctor):
    now = now_utc()
    active_tokens = db.execute(
        select(DoctorAccountRecovery).where(
            DoctorAccountRecovery.doctor_id == doctor.id,
            DoctorAccountRecovery.used_at.is_(None),
        )
    ).scalars().all()

    for active_token in active_tokens:
        active_token.used_at = to_utc(now)

    raw_token = secrets.token_urlsafe(32)
    recovery = DoctorAccountRecovery(
        doctor_id=doctor.id,
        token_hash=hash_token(raw_token),
        expires_at=to_utc(now + TOKEN_TTL),
    )
    db.add(recovery)
    db.commit()
    db.refresh(recovery)
    return raw_token, recovery
