from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, desc
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime import now_utc


class Vital(Base):
    __tablename__ = "vitals"
    __table_args__ = (
        Index("ix_vitals_patient_recorded_at_desc", "patient_id", desc("recorded_at")),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    heart_rate: Mapped[int] = mapped_column(Integer)
    oxygen_saturation: Mapped[int] = mapped_column(Integer)
    temperature: Mapped[int] = mapped_column(Integer)
    systolic_bp: Mapped[int] = mapped_column(Integer)
    diastolic_bp: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
