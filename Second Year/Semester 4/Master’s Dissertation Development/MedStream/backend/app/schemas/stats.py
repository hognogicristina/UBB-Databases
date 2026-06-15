from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.alert import AlertRead


class PatientStatsRead(BaseModel):
    patient_id: int
    avg_heart_rate: float
    avg_temperature: float
    avg_oxygen: float
    alerts_count: int
    treatment_outcomes: str | None = None
    computed_at: datetime
    model_config = {"from_attributes": True}


class BatchJobStatusRead(BaseModel):
    interval_seconds: int
    cron_expression: str | None = None
    last_run_started_at: datetime | None
    last_successful_run_at: datetime | None
    last_run_finished_at: datetime | None
    next_run_estimate: datetime | None
    next_run_in_seconds: int | None = None
    last_run_status: str
    last_run_error: str | None
    last_run_duration_ms: float | None
    stage: str | None = None


class BatchProgressRead(BaseModel):
    is_running: bool
    progress: int
    stage: str
    last_run: datetime | None
    last_run_status: str
    next_run_in_seconds: int | None = None


class BatchScheduleUpdate(BaseModel):
    type: str
    value: int | None = Field(default=None, ge=1, le=10080)
    time: str | None = None
    days: list[str] | None = None
    cron_expression: str | None = Field(default=None, min_length=9, max_length=100)


class BatchScheduleRead(BaseModel):
    type: str
    value: int | None = None
    time: str | None = None
    days: list[str] = Field(default_factory=list)
    cron_expression: str | None = None
    interval_seconds: int


class ComparisonMetricsRead(BaseModel):
    avg_heart_rate: float
    avg_oxygen: float
    avg_temperature: float
    avg_systolic_bp: float | None = None
    avg_diastolic_bp: float | None = None
    alerts: int
    patients_count: int | None = None
    timestamp: datetime | None = None
    execution_time_ms: float
    generated_discharge_summaries_count: int | None = None
    pending_discharge_summaries_count: int | None = None
    recent_vitals: list[dict] | None = None


class ComparisonSummaryRead(BaseModel):
    streaming_latency_avg: float
    batch_latency_avg: float
    total_events: int
    total_alerts: int
    events_per_second: float
    alert_rate: float
    batch_total_events: int | None = None
    batch_total_alerts: int | None = None
    batch_events_per_second: float | None = None
    batch_alert_rate: float | None = None


class ComparisonThroughputHistoryPointRead(BaseModel):
    time_iso: datetime
    time: str
    streaming_alerts_per_minute: int
    batch_alerts_per_minute: float | None = None
    batch_timestamp: datetime | None = None
    has_batch_snapshot: bool = False


class ComparisonLatencyHistoryPointRead(BaseModel):
    time_iso: datetime
    time: str
    streaming_latency_ms: float
    batch_latency_ms: float | None = None
    has_batch_snapshot: bool = False


class ComparisonHistoryRead(BaseModel):
    throughput: list[ComparisonThroughputHistoryPointRead]
    latency: list[ComparisonLatencyHistoryPointRead]


class PatientsPerDepartmentRead(BaseModel):
    department: str
    patients: int


class TopDiagnosisRead(BaseModel):
    name: str
    patients: int


class TreatmentEffectivenessRead(BaseModel):
    effective: int
    improving: int
    ineffective: int
    effective_rate: float | None = None
    improving_rate: float | None = None
    ineffective_rate: float | None = None


class MedicationEffectivenessRead(BaseModel):
    name: str
    effective: int
    improving: int
    ineffective: int
    total: int
    effective_rate: float | None = None
    improving_rate: float | None = None
    ineffective_rate: float | None = None
    total_patients: int
    alert_triggered_count: int
    diagnosis_triggered_count: int
    condition_triggered_count: int
    dosage_breakdown: list[dict[str, str | int]]


class PaginatedPatientsPerDepartmentRead(BaseModel):
    items: list[PatientsPerDepartmentRead]
    total: int
    page: int
    page_size: int


class PaginatedTopDiagnosisRead(BaseModel):
    items: list[TopDiagnosisRead]
    total: int
    page: int
    page_size: int


class BatchInsightsRead(BaseModel):
    patients_per_department: PaginatedPatientsPerDepartmentRead
    top_diagnosis: PaginatedTopDiagnosisRead
    treatment_effectiveness: TreatmentEffectivenessRead
    medication_effectiveness: list[MedicationEffectivenessRead]


class PaginatedStreamingAlertsRead(BaseModel):
    items: list[AlertRead]
    total: int
    page: int
    page_size: int


class BatchAlertsHistoryPointRead(BaseModel):
    timestamp: datetime
    critical: int
    high: int
    stable: int
    normalized: int | None = None
    total: int
