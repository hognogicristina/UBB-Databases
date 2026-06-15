from datetime import datetime

from pydantic import BaseModel


class PatientAdmissionActionCreate(BaseModel):
    arrival_method: str


class PatientAdmissionHistoryRead(BaseModel):
    id: int
    patient_id: int
    doctor_id: int | None = None
    type: str
    reason: str | None = None
    note: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class PatientAdmissionHistoryPage(BaseModel):
    items: list[PatientAdmissionHistoryRead]
    total: int
    page: int
    page_size: int
