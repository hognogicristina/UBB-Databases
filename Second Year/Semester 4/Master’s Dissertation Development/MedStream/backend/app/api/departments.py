from fastapi import APIRouter
from app.core.http import success_response
from app.service.clinical_records import load_departments

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("")
def list_departments():
    departments = load_departments()
    return success_response("Departments retrieved successfully.", departments)
