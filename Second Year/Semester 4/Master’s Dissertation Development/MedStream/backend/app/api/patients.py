from fastapi import APIRouter, Header, Query

from app.api.activity_utils import serialize_activities
from app.core.error_handling import raise_http_from_error
from app.api.doctors import get_current_doctor
from app.core.http import ApiResponse, success_response
from app.schemas.doctor import DoctorRead
from app.schemas.doctor_activity import DoctorActivityRead
from app.schemas.patient import (
    PatientCreate,
    PatientDepartmentUpdate,
    PatientDischargeUpdate,
    PatientRead,
    PatientTransferRequest,
    PatientUpdate,
)
from app.schemas.patient_admission_history import (
    PatientAdmissionActionCreate,
    PatientAdmissionHistoryPage,
    PatientAdmissionHistoryRead,
)
from app.schemas.patient_allergy import PatientAllergyCreate, PatientAllergyPage, PatientAllergyRead, PatientAllergyUpdate
from app.schemas.patient_condition import (
    ConditionUpdate,
    PatientConditionAssignmentCreate,
    PatientConditionAssignmentRead,
    PatientConditionRead,
)
from app.schemas.patient_diagnosis import (
    PatientDiagnosisCreate,
    PatientDiagnosisPage,
    PatientDiagnosisRead,
    PatientDiagnosisUpdate,
)
from app.schemas.patient_medication import MedicationUpdate, PatientMedicationCreate, PatientMedicationRead
from app.schemas.patient_treatment_analysis import PatientSearchResultRead, PatientTreatmentAnalysisRead
from app.schemas.patient_post_discharge_summary import PatientPostDischargeSummaryRead
from app.service.clinical_records import (
    ACTIVITY_TYPES,
    ALLERGIES,
    DIAGNOSIS,
    DISCHARGE,
    DOSAGES,
    DRUGS,
    STATUS,
)
from app.service.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])
option_router = APIRouter(tags=["auth"])
patient_service = PatientService()


def serialize(model, schema):
    return schema.model_validate(model, from_attributes=True).model_dump(mode="json")


def serialize_many(models, schema):
    return [serialize(model, schema) for model in models]


def build_paginated_payload(items, total: int, page: int, page_size: int, schema):
    return {
        "items": serialize_many(items, schema),
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def doctor_name_map(doctors):
    return {
        doctor.id: f"{doctor.last_name} {doctor.first_name}".strip()
        for doctor in doctors
    }


def serialize_condition_rows(rows, doctor_names: dict[int, str] | None = None):
    doctor_names = doctor_names or {}
    payload = []
    for condition, assignment in rows:
        modified_by = getattr(assignment, "modified_by", None) or doctor_names.get(assignment.doctor_id)
        payload.append(
            PatientConditionRead.model_validate(
                {
                    **serialize(condition, PatientConditionRead),
                    "assignment_id": assignment.id,
                    "doctor_id": assignment.doctor_id,
                    "modified_by": modified_by,
                    "status": assignment.status,
                    "notes": assignment.notes,
                    "diagnosed_at": assignment.diagnosed_at,
                    "updated_at": assignment.updated_at,
                }
            ).model_dump(mode="json")
        )
    return payload


@router.get("", response_model=ApiResponse[list[PatientRead]])
def list_patients(
    condition_id: int | None = Query(default=None, ge=1),
    department: str | None = Query(default=None),
    alert_presence: str | None = Query(default="all", pattern="^(all|critical|high|normal|any|none)$"),
    status: str | None = Query(default="all", pattern="^(all|admitted|discharged)$"),
    treatment_outcome: str | None = Query(default="all", pattern="^(all|effective|improving|ineffective)$"),
):
    try:
        patients = patient_service.list_patients(condition_id, department, alert_presence, status, treatment_outcome)
        return success_response("Patients retrieved successfully.", serialize_many(patients, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/search", response_model=ApiResponse[list[PatientSearchResultRead]])
def search_patients(cnp: str = Query(default="", min_length=1, max_length=32)):
    try:
        patients = patient_service.search_patients_by_cnp(cnp)
        payload = [
            {
                "id": patient.id,
                "cnp": patient.cnp,
                "full_name": f"{patient.last_name} {patient.first_name}".strip(),
            }
            for patient in patients
        ]
        return success_response("Patient search completed successfully.", payload)
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}", response_model=ApiResponse[PatientRead])
def get_patient(id: int):
    try:
        patient = patient_service.get_patient(id)
        return success_response("Patient retrieved successfully.", serialize(patient, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/treatment-analysis", response_model=ApiResponse[PatientTreatmentAnalysisRead])
def get_patient_treatment_analysis(id: int):
    try:
        analysis = patient_service.get_patient_treatment_analysis(id)
        return success_response("Patient treatment analysis retrieved successfully.", analysis)
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/post-discharge-summary", response_model=ApiResponse[PatientPostDischargeSummaryRead])
def get_patient_post_discharge_summary(id: int):
    try:
        summary = patient_service.get_patient_post_discharge_summary(id)
        status = summary.get("status")
        if status == "ready":
            message = "Post-discharge clinical summary retrieved successfully."
        elif status == "pending":
            message = "Post-discharge clinical summary is pending batch generation."
        else:
            message = "Post-discharge clinical summary is not available yet."
        return success_response(message, summary)
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/doctors", response_model=ApiResponse[list[DoctorRead]])
def get_patient_doctors(id: int):
    try:
        doctors = patient_service.get_patient_doctors(id)
        return success_response("Patient doctors retrieved successfully.", serialize_many(doctors, DoctorRead))
    except Exception as error:
        raise_http_from_error(error)


@router.post("", response_model=ApiResponse[PatientRead])
def create_patient(payload: PatientCreate, authorization: str | None = Header(default=None)):
    current_doctor = None
    if authorization:
        current_doctor = get_current_doctor(authorization)
    try:
        patient = patient_service.create_patient(payload.model_dump(), current_doctor.id if current_doctor else None)
        return success_response("Patient created successfully.", serialize(patient, PatientRead), status_code=201)
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/{id}", response_model=ApiResponse[PatientRead])
def update_patient(id: int, payload: PatientUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        patient = patient_service.update_patient(id, current_doctor.id, payload.model_dump(exclude_unset=True))
        return success_response("Patient updated successfully.", serialize(patient, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/{id}/department", response_model=ApiResponse[PatientRead])
def update_patient_department(id: int, payload: PatientDepartmentUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        patient = patient_service.update_patient_department(id, current_doctor.id, payload.department, payload.reason)
        return success_response("Patient department updated successfully.", serialize(patient, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/{id}/discharge", response_model=ApiResponse[PatientRead])
def discharge_patient(id: int, payload: PatientDischargeUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        patient = patient_service.discharge_patient(id, current_doctor.id, payload.type, payload.reason)
        return success_response("Patient discharged successfully.", serialize(patient, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{id}/readmit", response_model=ApiResponse[PatientRead])
def readmit_patient(id: int, payload: PatientAdmissionActionCreate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        patient = patient_service.readmit_patient(
            id,
            current_doctor.id,
            current_doctor.specialization,
            payload.arrival_method,
        )
        return success_response("Patient readmitted successfully.", serialize(patient, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{id}/transfer", response_model=ApiResponse[PatientRead])
def transfer_patient(id: int, payload: PatientTransferRequest, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        patient = patient_service.transfer_patient_assignment(
            id,
            current_doctor.id,
            payload.from_doctor_id,
            payload.to_doctor_id,
        )
        return success_response("Patient transferred successfully.", serialize(patient, PatientRead))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/admission-history", response_model=ApiResponse[PatientAdmissionHistoryPage])
def get_patient_admission_history(
        id: int,
        page: int = Query(1, ge=1),
        page_size: int = Query(5, ge=1, le=100),
):
    try:
        entries, total = patient_service.get_patient_admission_history(id, page, page_size)
        return success_response(
            "Patient admission history retrieved successfully.",
            build_paginated_payload(entries, total, page, page_size, PatientAdmissionHistoryRead),
        )
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/conditions", response_model=ApiResponse[list[PatientConditionRead]])
def get_patient_conditions(id: int):
    try:
        rows = patient_service.get_patient_conditions(id)
        doctors = patient_service.get_patient_doctors(id)
        return success_response(
            "Patient conditions retrieved successfully.",
            serialize_condition_rows(rows, doctor_name_map(doctors)),
        )
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{id}/conditions", response_model=ApiResponse[list[PatientConditionRead]])
def assign_patient_condition(id: int, payload: PatientConditionAssignmentCreate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        rows = patient_service.assign_patient_condition(id, payload.condition_id, current_doctor.id)
        doctors = patient_service.get_patient_doctors(id)
        return success_response(
            "Patient condition assigned successfully.",
            serialize_condition_rows(rows, doctor_name_map(doctors)),
        )
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/condition/{assignment_id}", response_model=ApiResponse[PatientConditionAssignmentRead])
def update_condition_assignment(assignment_id: int, payload: ConditionUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        assignment = patient_service.update_condition_assignment(assignment_id, current_doctor.id, payload.status, payload.notes)
        return success_response("Condition updated successfully.", serialize(assignment, PatientConditionAssignmentRead))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/allergies", response_model=ApiResponse[PatientAllergyPage])
def get_patient_allergies(id: int, page: int = Query(1, ge=1), page_size: int = Query(5, ge=1, le=100)):
    try:
        allergies, total = patient_service.get_patient_allergies(id, page, page_size)
        return success_response(
            "Patient allergies retrieved successfully.",
            build_paginated_payload(allergies, total, page, page_size, PatientAllergyRead),
        )
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{id}/allergies", response_model=ApiResponse[PatientAllergyRead])
def create_patient_allergy(id: int, payload: PatientAllergyCreate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        allergy = patient_service.create_patient_allergy(id, current_doctor.id, payload.allergy_name, payload.severity)
        return success_response("Patient allergy added successfully.", serialize(allergy, PatientAllergyRead), status_code=201)
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/diagnosis", response_model=ApiResponse[PatientDiagnosisPage])
def get_patient_diagnosis(id: int, page: int = Query(1, ge=1), page_size: int = Query(5, ge=1, le=100)):
    try:
        diagnosis_entries, total = patient_service.get_patient_diagnosis(id, page, page_size)
        items = []
        for diagnosis in diagnosis_entries:
            item = serialize(diagnosis, PatientDiagnosisRead)
            item["modified_by"] = getattr(diagnosis, "modified_by", None)
            items.append(item)
        return success_response(
            "Patient diagnosis retrieved successfully.",
            {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        )
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{id}/diagnosis", response_model=ApiResponse[PatientDiagnosisRead])
def create_patient_diagnosis(id: int, payload: PatientDiagnosisCreate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        diagnosis_entry = patient_service.create_patient_diagnosis(id, current_doctor.id, payload.diagnosis, payload.notes)
        result = serialize(diagnosis_entry, PatientDiagnosisRead)
        result["modified_by"] = f"{current_doctor.last_name} {current_doctor.first_name}".strip()
        return success_response(
            "Patient diagnosis added successfully.",
            result,
            status_code=201,
        )
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/diagnosis/{diagnosis_id}", response_model=ApiResponse[PatientDiagnosisRead])
def update_patient_diagnosis(diagnosis_id: int, payload: PatientDiagnosisUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        diagnosis = patient_service.update_patient_diagnosis(
            diagnosis_id,
            current_doctor.id,
            payload.status,
            payload.note,
            payload.notes,
        )
        result = serialize(diagnosis, PatientDiagnosisRead)
        result["modified_by"] = f"{current_doctor.last_name} {current_doctor.first_name}".strip()
        return success_response("Diagnosis updated successfully.", result)
    except Exception as error:
        raise_http_from_error(error)


@router.post("/{id}/medication", response_model=ApiResponse[PatientMedicationRead])
def administer_medication(id: int, payload: PatientMedicationCreate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        medication = patient_service.administer_medication(
            id,
            current_doctor.id,
            payload.name,
            payload.dosage,
            payload.frequency,
            payload.notes,
        )
        return success_response("Medication administered successfully.", serialize(medication, PatientMedicationRead), status_code=201)
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/medications", response_model=ApiResponse[list[PatientMedicationRead]])
def get_patient_medications(id: int):
    try:
        meds = patient_service.get_patient_medications(id)
        return success_response("Patient medications retrieved successfully.", serialize_many(meds, PatientMedicationRead))
    except Exception as error:
        raise_http_from_error(error)


@router.get("/{id}/activities", response_model=ApiResponse[list[DoctorActivityRead]])
def get_patient_activities(id: int):
    try:
        activities = patient_service.get_patient_activities(id)
        return success_response("Patient activities retrieved successfully.", serialize_activities(activities))
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/medications/{medication_id}", response_model=ApiResponse[PatientMedicationRead])
def update_medication(medication_id: int, payload: MedicationUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        medication = patient_service.update_medication(
            medication_id,
            current_doctor.id,
            payload.dosage,
            payload.frequency,
            payload.note,
        )
        return success_response("Medication updated successfully.", serialize(medication, PatientMedicationRead))
    except Exception as error:
        raise_http_from_error(error)


@router.patch("/allergies/{allergy_id}", response_model=ApiResponse[PatientAllergyRead])
def update_patient_allergy(allergy_id: int, payload: PatientAllergyUpdate, authorization: str | None = Header(default=None)):
    current_doctor = get_current_doctor(authorization)
    try:
        allergy = patient_service.update_patient_allergy(allergy_id, current_doctor.id, payload.severity)
        return success_response("Allergy updated successfully.", serialize(allergy, PatientAllergyRead))
    except Exception as error:
        raise_http_from_error(error)


@option_router.get("/options/diagnosis")
def get_diagnosis_options():
    return success_response("Diagnosis options", DIAGNOSIS)


@option_router.get("/options/allergies")
def get_allergy_options():
    return success_response("Allergy options", ALLERGIES)


@option_router.get("/options/medications")
def get_medication_options():
    meds = list({d["medication"] for d in DRUGS})
    return success_response("Medication options", meds)


@option_router.get("/options/dosages")
def get_dosage_options():
    return success_response("Dosage options", DOSAGES)


@option_router.get("/options/conditions")
def get_condition_options():
    try:
        conditions = patient_service.get_condition_options()
        return success_response("Condition options", serialize_many(conditions, PatientConditionRead))
    except Exception as error:
        raise_http_from_error(error)


@option_router.get("/options/activities")
def get_activity_options():
    return success_response("Activity type options", ACTIVITY_TYPES)


@option_router.get("/options/condition-statuses")
def get_condition_status_options():
    return success_response("Condition status options", STATUS)


@option_router.get("/discharge-types")
def get_discharge_types():
    return success_response("Discharge types retrieved successfully.", DISCHARGE)
