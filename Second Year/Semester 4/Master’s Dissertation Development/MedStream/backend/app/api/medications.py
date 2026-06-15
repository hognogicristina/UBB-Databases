from fastapi import APIRouter, HTTPException

from app.core.http import ApiResponse, success_response
from app.db.session import SessionLocal
from app.models.patient.patient import Patient
from app.service.clinical_records import DOSAGES, DRUGS, FREQUENCIES

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("/frequencies", response_model=ApiResponse[list[str]])
def get_medication_frequencies():
    return success_response("Medication frequencies retrieved successfully.", FREQUENCIES)


@router.get("/dosages", response_model=ApiResponse[list[str]])
def get_medication_dosages():
    return success_response("Medication dosages retrieved successfully.", DOSAGES)


@router.get("/patients/{patient_id}/options", response_model=ApiResponse[list[dict]])
def get_patient_medication_options(patient_id: int):
    with SessionLocal() as db:
        patient = db.get(Patient, patient_id)

        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found.")

        allowed_categories = {"A", "B"} if patient.is_pregnant else {"A", "B", "C", "D", "N"}

        medications = []
        seen = set()
        for drug in DRUGS:
            pregnancy_category = (drug.get("pregnancy_category") or "N").strip() or "N"

            if pregnancy_category not in allowed_categories:
                continue

            key = (drug["medication"], pregnancy_category)
            if key in seen:
                continue

            seen.add(key)
            medications.append({
                "name": drug["medication"],
                "pregnancy_category": pregnancy_category,
            })

        medications.sort(key=lambda item: item["name"].lower())
        return success_response("Medication options retrieved successfully.", medications)
