from fastapi import APIRouter
from sqlalchemy import select

from app.batch.status import batch_status_store
from app.core.http import ApiResponse, success_response
from app.db.session import SessionLocal
from app.models.patient.patient_stats import PatientStats
from app.schemas.stats import BatchJobStatusRead, PatientStatsRead

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=ApiResponse[list[PatientStatsRead]])
def get_stats():
    with SessionLocal() as db:
        stats = db.execute(select(PatientStats)).scalars().all()
        return success_response(
            "Patient statistics retrieved successfully.",
            [PatientStatsRead.model_validate(stat).model_dump(mode="json") for stat in stats],
        )


@router.get("/batch-status", response_model=ApiResponse[BatchJobStatusRead])
def get_batch_status():
    return success_response(
        "Batch status retrieved successfully.",
        BatchJobStatusRead.model_validate(batch_status_store.snapshot()).model_dump(mode="json"),
    )
