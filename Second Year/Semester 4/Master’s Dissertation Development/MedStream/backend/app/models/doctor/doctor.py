from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.doctor.doctor_activity_patient import doctor_activity_patients


class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    pending_email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    phone_number: Mapped[str | None] = mapped_column(String(50), unique=True, index=True, nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    specialization: Mapped[str] = mapped_column(String(100))
    license_number: Mapped[str] = mapped_column(String(50), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    patients: Mapped[list["Patient"]] = relationship("Patient", secondary=doctor_activity_patients, back_populates="doctors")
