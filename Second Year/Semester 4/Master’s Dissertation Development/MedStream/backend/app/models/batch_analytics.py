from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime import now_utc


class BatchAnalytics(Base):
    __tablename__ = "batch_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    avg_heart_rate: Mapped[float] = mapped_column(Float)
    avg_oxygen: Mapped[float] = mapped_column(Float)
    avg_temperature: Mapped[float] = mapped_column(Float)
    avg_systolic_bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_diastolic_bp: Mapped[float | None] = mapped_column(Float, nullable=True)
    alerts_count: Mapped[int] = mapped_column(Integer)
    alerts_critical_count: Mapped[int] = mapped_column(Integer, default=0)
    alerts_high_count: Mapped[int] = mapped_column(Integer, default=0)
    alerts_stable_count: Mapped[int] = mapped_column(Integer, default=0)
    patients_count: Mapped[int] = mapped_column(Integer)
    total_events_count: Mapped[int] = mapped_column(Integer, default=0)
    events_per_second: Mapped[float] = mapped_column(Float, default=0.0)
    alert_rate: Mapped[float] = mapped_column(Float, default=0.0)
    batch_latency_avg_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    patients_per_department_snapshot: Mapped[list[dict]] = mapped_column(JSON, default=list)
    top_diagnosis_snapshot: Mapped[list[dict]] = mapped_column(JSON, default=list)
    treatment_effectiveness_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    medication_effectiveness_snapshot: Mapped[list[dict]] = mapped_column(JSON, default=list)
