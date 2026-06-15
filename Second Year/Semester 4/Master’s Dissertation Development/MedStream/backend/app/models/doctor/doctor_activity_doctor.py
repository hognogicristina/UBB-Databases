from sqlalchemy import Column, ForeignKey, Integer, Table

from app.db.base import Base

doctor_activity_doctors = Table(
    "doctor_activity_doctors",
    Base.metadata,
    Column("doctor_activity_id", Integer, ForeignKey("doctor_activities.id", ondelete="CASCADE"), primary_key=True),
    Column("doctor_id", Integer, ForeignKey("doctors.id", ondelete="CASCADE"), primary_key=True),
)
