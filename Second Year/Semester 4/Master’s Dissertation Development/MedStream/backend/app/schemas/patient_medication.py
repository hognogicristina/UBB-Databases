from datetime import datetime

from pydantic import BaseModel


class PatientMedicationCreate(BaseModel):
    name: str
    dosage: str
    frequency: str
    notes: str | None = None


class PatientMedicationRead(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    name: str
    dosage: str
    frequency: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    last_updated_note: str | None = None
    model_config = {"from_attributes": True}


class MedicationUpdate(BaseModel):
    dosage: str | None = None
    frequency: str | None = None
    note: str
