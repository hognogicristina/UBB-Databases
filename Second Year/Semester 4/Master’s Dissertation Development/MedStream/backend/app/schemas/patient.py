from datetime import date, datetime

from pydantic import BaseModel, Field


class PatientAddressBase(BaseModel):
    street: str = Field(max_length=120)
    number: str = Field(max_length=30)
    apartment: str | None = Field(default=None, max_length=30)
    city: str = Field(max_length=100)
    county: str = Field(max_length=100)
    postal_code: str = Field(max_length=20)


class PatientAddressCreate(PatientAddressBase):
    pass


class PatientAddressRead(BaseModel):
    street: str | None = None
    number: str | None = None
    apartment: str | None = None
    city: str | None = None
    county: str | None = None
    postal_code: str | None = None
    country: str = "Romania"

    model_config = {"from_attributes": True}


class PatientAddressUpdate(BaseModel):
    street: str | None = Field(default=None, max_length=120)
    number: str | None = Field(default=None, max_length=30)
    apartment: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=100)
    county: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)


class PatientBase(BaseModel):
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    department: str = Field(max_length=50)
    cnp: str
    phone_number: str
    birth_date: date
    gender: str = Field(max_length=20)
    arrival_method: str = Field(default="self", max_length=20)
    is_pregnant: bool = False
    address: PatientAddressCreate


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=50)
    cnp: str | None = None
    phone_number: str | None = None
    birth_date: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    is_pregnant: bool | None = None
    address: PatientAddressUpdate | None = None


class PatientRead(PatientBase):
    id: int
    phone_number: str | None = None
    address: PatientAddressRead | None = None
    is_discharged: bool = False
    discharge_reason: str | None = None
    discharge_date: datetime | None = None

    model_config = {"from_attributes": True}


class PatientDepartmentUpdate(BaseModel):
    department: str
    reason: str


class PatientDischargeUpdate(BaseModel):
    type: str
    reason: str


class PatientTransferRequest(BaseModel):
    from_doctor_id: int
    to_doctor_id: int
