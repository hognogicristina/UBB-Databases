from datetime import datetime

from pydantic import BaseModel
from typing import Any, Literal


class PatientSearchResultRead(BaseModel):
    id: int
    cnp: str
    full_name: str


class TreatmentMedicationReasoningRead(BaseModel):
    alerts: list[str]
    diagnoses: list[str]
    conditions: list[str]


class TreatmentMedicationRead(BaseModel):
    class TreatmentLinkedAlertRead(BaseModel):
        alert_type: str
        severity: str
        message: str
        created_at: datetime

    class TreatmentSelectedVitalRead(BaseModel):
        heart_rate: float | None = None
        oxygen_saturation: float | None = None
        temperature: float | None = None

    id: int
    action: Literal["add", "modify"] | None = None
    name: str
    dosage: str
    frequency: str
    created_at: datetime | None = None
    prescribed_at: datetime
    timestamp: datetime | None = None
    updated_at: datetime | None = None
    notes: str | None = None
    last_updated_note: str | None = None
    modified_by: str | None = None
    treatment_index: int | None = None
    outcome: Literal["Effective", "Improving", "Ineffective"] | None = None
    selected_vital_source: str | None = None
    selected_vital_timestamp: datetime | None = None
    selected_vital: TreatmentSelectedVitalRead | None = None
    evaluation_start: datetime | None = None
    evaluation_end: datetime | None = None
    evaluated_vital_timestamp: datetime | None = None
    evaluated_vital: TreatmentSelectedVitalRead | None = None
    outcome_reason: str | None = None
    outcome_evidence: dict[str, Any] | None = None
    recovered_vitals: list[str] | None = None
    unresolved_vitals: list[str] | None = None
    latest_alerts: dict[str, Any] | None = None
    previous_alert: TreatmentLinkedAlertRead | None = None
    next_alert: TreatmentLinkedAlertRead | None = None
    reasoning: TreatmentMedicationReasoningRead


class TreatmentDiagnosisRead(BaseModel):
    id: int
    diagnosis: str
    status: str
    notes: str | None = None
    status_note: str | None = None
    modified_by: str | None = None
    created_at: datetime


class TreatmentConditionRead(BaseModel):
    id: int
    name: str
    status: str
    notes: str | None = None
    modified_by: str | None = None
    diagnosed_at: datetime | None = None
    updated_at: datetime | None = None


class TreatmentAlertRead(BaseModel):
    class StatusVitalsRead(BaseModel):
        heartRate: float | None = None
        oxygen: float | None = None
        temperature: float | None = None

    id: int
    alert_type: str
    type: Literal["heart_rate", "oxygen_saturation", "temperature"] | None = None
    value: float | None = None
    unit: str | None = None
    vitals: StatusVitalsRead | None = None
    message: str
    severity: str
    created_at: datetime


class TreatmentTimelineEventRead(BaseModel):
    timestamp: datetime
    event_type: str
    title: str
    details: str | None = None
    related_medication_id: int | None = None


class PatientTreatmentAnalysisRead(BaseModel):
    medications: list[TreatmentMedicationRead]
    diagnoses: list[TreatmentDiagnosisRead]
    conditions: list[TreatmentConditionRead]
    alerts: list[TreatmentAlertRead]
    timeline: list[TreatmentTimelineEventRead]
