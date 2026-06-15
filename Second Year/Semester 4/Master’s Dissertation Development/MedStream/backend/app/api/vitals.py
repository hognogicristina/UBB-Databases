from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.http import ApiResponse, success_response
from app.db.session import SessionLocal
from app.models.vital import Vital
from app.schemas.vital import VitalTimelineRead

router = APIRouter(prefix="/vitals", tags=["vitals"])


@router.get("", response_model=ApiResponse[list[VitalTimelineRead]])
def list_vitals(
        patient_id: int = Query(..., ge=1),
        limit: int = Query(default=100, ge=1, le=100),
):
    with SessionLocal() as db:
        vitals = db.execute(
            select(
                Vital.recorded_at,
                Vital.heart_rate,
                Vital.oxygen_saturation,
                Vital.temperature,
            )
            .where(Vital.patient_id == patient_id)
            .order_by(Vital.recorded_at.desc())
            .limit(limit)
        ).all()
        return success_response(
            "Vitals retrieved successfully.",
            [
                VitalTimelineRead(
                    recorded_at=vital.recorded_at,
                    heart_rate=vital.heart_rate,
                    oxygen_saturation=vital.oxygen_saturation,
                    temperature=vital.temperature,
                ).model_dump(mode="json")
                for vital in vitals
            ],
        )
