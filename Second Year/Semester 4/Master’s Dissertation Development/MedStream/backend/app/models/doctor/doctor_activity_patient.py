from sqlalchemy import ForeignKey, Table, Column, Integer

from app.db.base import Base

doctor_activity_patients = Table(
    "doctor_activity_patients",
    Base.metadata,
    Column("doctor_id", Integer, ForeignKey("doctors.id"), primary_key=True),
    Column("patient_id", Integer, ForeignKey("patients.id"), primary_key=True),
)
