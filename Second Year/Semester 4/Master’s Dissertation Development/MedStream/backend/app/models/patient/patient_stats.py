from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime import now_utc


class PatientStats(Base):
    __tablename__ = "patient_stats"
    __table_args__ = (
        Index("ix_patient_stats_patient_id", "patient_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(Integer)
    avg_heart_rate: Mapped[float] = mapped_column(Float)
    avg_temperature: Mapped[float] = mapped_column(Float)
    avg_oxygen: Mapped[float] = mapped_column(Float)
    alerts_count: Mapped[int] = mapped_column(Integer)
    treatment_outcomes: Mapped[str] = mapped_column(String(100), default="")
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
