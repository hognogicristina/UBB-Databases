from datetime import datetime

from pydantic import BaseModel


class PatientAllergyCreate(BaseModel):
    allergy_name: str
    severity: str


class PatientAllergyRead(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    allergy_name: str
    severity: str
    status: str = "Unknown"
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class PatientAllergyPage(BaseModel):
    items: list[PatientAllergyRead]
    total: int
    page: int
    page_size: int


class PatientAllergyUpdate(BaseModel):
    severity: str | None = None
