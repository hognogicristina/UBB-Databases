from datetime import datetime

from pydantic import BaseModel


class AlertRead(BaseModel):
    id: int
    patient_id: int
    vital_id: int
    alert_type: str
    message: str
    severity: str
    created_at: datetime
    event_time: datetime | None = None
    model_config = {"from_attributes": True}


class AlertDashboardSummary(BaseModel):
    total_alerts: int
    preview_alerts: list[AlertRead]
