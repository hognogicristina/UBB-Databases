from datetime import datetime

from pydantic import BaseModel


class PatientDiagnosisCreate(BaseModel):
    diagnosis: str
    notes: str | None = None


class PatientDiagnosisRead(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    modified_by: str | None = None
    diagnosis: str
    notes: str | None = None
    status: str
    status_note: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class PatientDiagnosisPage(BaseModel):
    items: list[PatientDiagnosisRead]
    total: int
    page: int
    page_size: int


class PatientDiagnosisUpdate(BaseModel):
    status: str | None = None
    note: str | None = None
    notes: str | None = None
