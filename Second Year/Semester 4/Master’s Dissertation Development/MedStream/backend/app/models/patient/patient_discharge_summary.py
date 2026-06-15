from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime import now_utc


class PatientDischargeSummary(Base):
    __tablename__ = "patient_discharge_summaries"
    __table_args__ = (
        UniqueConstraint("patient_id", "discharge_date", name="uq_patient_discharge_summary_episode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    discharge_date: Mapped[datetime] = mapped_column(DateTime)
    discharge_reason: Mapped[str] = mapped_column(Text, default="")
    total_alerts: Mapped[int] = mapped_column(Integer, default=0)
    critical_alerts: Mapped[int] = mapped_column(Integer, default=0)
    high_alerts: Mapped[int] = mapped_column(Integer, default=0)
    normal_alerts: Mapped[int] = mapped_column(Integer, default=0)
    normalized_alerts: Mapped[int] = mapped_column(Integer, default=0)
    total_treatments: Mapped[int] = mapped_column(Integer, default=0)
    effective_treatments: Mapped[int] = mapped_column(Integer, default=0)
    improving_treatments: Mapped[int] = mapped_column(Integer, default=0)
    ineffective_treatments: Mapped[int] = mapped_column(Integer, default=0)
    most_problematic_vital: Mapped[str] = mapped_column(String(64), default="none")
    final_treatment_outcome: Mapped[str] = mapped_column(String(64), default="Not available")
    final_patient_state: Mapped[str] = mapped_column(String(255), default="No clinical state available.")
    clinical_summary: Mapped[str] = mapped_column(Text, default="")
    readmission_notes: Mapped[str] = mapped_column(Text, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now_utc, onupdate=now_utc)
