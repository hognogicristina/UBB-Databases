from datetime import datetime

from pydantic import BaseModel


class DoctorActivityParticipantRead(BaseModel):
    id: int
    first_name: str
    last_name: str


class PatientActivityParticipantRead(BaseModel):
    id: int
    first_name: str
    last_name: str


class DoctorActivityCreate(BaseModel):
    type: str
    title: str
    description: str | None = None
    scheduled_at: datetime
    patient_ids: list[int]
    doctor_ids: list[int]


class DoctorActivityRead(BaseModel):
    id: int
    doctor_id: int
    patient_id: int | None = None
    type: str
    title: str
    description: str | None = None
    scheduled_at: datetime
    created_at: datetime
    status: str
    patient_ids: list[int]
    doctor_ids: list[int]
    patients: list[PatientActivityParticipantRead] = []
    doctors: list[DoctorActivityParticipantRead] = []

    model_config = {"from_attributes": True}


class DoctorActivityUpdate(BaseModel):
    type: str | None = None
    title: str | None = None
    description: str | None = None
    scheduled_at: datetime | None = None
    status: str | None = None
    doctor_ids: list[int] | None = None
