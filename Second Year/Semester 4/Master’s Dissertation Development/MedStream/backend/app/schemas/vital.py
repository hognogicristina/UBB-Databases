from datetime import datetime

from pydantic import BaseModel


class VitalCreate(BaseModel):
    patient_id: int
    heart_rate: int
    oxygen_saturation: int
    temperature: int
    systolic_bp: int
    diastolic_bp: int


class VitalTimelineRead(BaseModel):
    recorded_at: datetime
    heart_rate: int
    oxygen_saturation: int
    temperature: int
