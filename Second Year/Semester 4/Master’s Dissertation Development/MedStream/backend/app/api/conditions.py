from fastapi import APIRouter
from sqlalchemy import select

from app.core.http import ApiResponse, success_response
from app.db.session import SessionLocal
from app.models.patient.patient_condition import PatientCondition
from app.schemas.patient_condition import PatientConditionRead

router = APIRouter(prefix="/conditions", tags=["conditions"])


@router.get("", response_model=ApiResponse[list[PatientConditionRead]])
def list_conditions():
    with SessionLocal() as db:
        conditions = db.execute(
            select(PatientCondition).order_by(PatientCondition.name.asc(), PatientCondition.id.asc())
        ).scalars().all()
        payload = [PatientConditionRead.model_validate(condition).model_dump(mode="json") for condition in conditions]
        return success_response("Conditions retrieved successfully.", payload)
