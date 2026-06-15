from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PostDischargeAlertMetricsRead(BaseModel):
    total: int
    critical: int
    high: int
    normal: int
    normalized: int


class PostDischargeTreatmentMetricsRead(BaseModel):
    total: int
    effective: int
    improving: int
    ineffective: int


class PatientPostDischargeSummaryRead(BaseModel):
    status: Literal["ready", "pending", "not_available"]
    patient_id: int
    discharge_date: datetime | None = None
    discharge_reason: str | None = None
    alert_metrics: PostDischargeAlertMetricsRead | None = None
    treatment_metrics: PostDischargeTreatmentMetricsRead | None = None
    most_problematic_vital: str | None = None
    final_treatment_outcome: str | None = None
    final_patient_state: str | None = None
    clinical_summary: str | None = None
    readmission_notes: str | None = None
    generated_at: datetime | None = None
    updated_at: datetime | None = None
