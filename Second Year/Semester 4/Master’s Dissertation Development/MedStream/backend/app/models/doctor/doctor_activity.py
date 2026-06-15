from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.doctor.doctor_activity_patient import doctor_activity_patients
from app.models.patient.patient_activity_doctor import patient_activity_doctors
from app.models.doctor.doctor_activity_doctor import doctor_activity_doctors
from app.utils.datetime import now_utc


class DoctorActivity(Base):
    __tablename__ = "doctor_activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    patient_id = mapped_column(ForeignKey("patients.id"))
    type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="incoming")
    scheduled_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)

    patients = relationship(
        "Patient",
        secondary=patient_activity_doctors,
        back_populates="activities"
    )

    doctors = relationship(
        "Doctor",
        secondary=doctor_activity_doctors
    )
