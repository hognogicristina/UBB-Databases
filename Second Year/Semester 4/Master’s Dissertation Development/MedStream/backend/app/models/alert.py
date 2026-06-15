from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime import now_utc


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_patient_created_at", "patient_id", "created_at"),
        Index("ix_alerts_created_at_desc", "created_at"),
        Index("ix_alerts_severity_created_at", "severity", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    vital_id: Mapped[int] = mapped_column(ForeignKey("vitals.id"))
    alert_type: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20), default="high")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
