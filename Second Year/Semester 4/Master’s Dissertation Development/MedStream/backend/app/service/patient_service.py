from __future__ import annotations

from app.repositories.patient_repository import PatientRepository


class PatientService:
    def __init__(self, repository: PatientRepository | None = None):
        self.repository = repository or PatientRepository()

    def list_patients(
        self,
        condition_id: int | None = None,
        department: str | None = None,
        alert_presence: str | None = None,
        status: str | None = None,
        treatment_outcome: str | None = None,
    ):
        return self.repository.list_patients(
            condition_id=condition_id,
            department=department,
            alert_presence=alert_presence,
            status=status,
            treatment_outcome=treatment_outcome,
        )

    def search_patients_by_cnp(self, cnp: str):
        return self.repository.search_patients_by_cnp(cnp)

    def get_patient(self, patient_id: int):
        return self.repository.get_patient(patient_id)

    def get_patient_treatment_analysis(self, patient_id: int):
        return self.repository.get_patient_treatment_analysis(patient_id)

    def get_patient_post_discharge_summary(self, patient_id: int):
        return self.repository.get_patient_post_discharge_summary(patient_id)

    def get_patient_doctors(self, patient_id: int):
        return self.repository.get_patient_doctors(patient_id)

    def create_patient(self, payload: dict, doctor_id: int | None = None):
        return self.repository.create_patient(payload, doctor_id)

    def update_patient(self, patient_id: int, doctor_id: int, payload: dict):
        return self.repository.update_patient(patient_id, doctor_id, payload)

    def update_patient_department(self, patient_id: int, doctor_id: int, department: str, reason: str):
        return self.repository.update_patient_department(patient_id, doctor_id, department, reason)

    def discharge_patient(self, patient_id: int, doctor_id: int, discharge_type: str, reason: str):
        return self.repository.discharge_patient(patient_id, doctor_id, discharge_type, reason)

    def readmit_patient(self, patient_id: int, doctor_id: int, doctor_specialization: str, arrival_method: str):
        return self.repository.readmit_patient(patient_id, doctor_id, doctor_specialization, arrival_method)

    def transfer_patient_assignment(self, patient_id: int, current_doctor_id: int, from_doctor_id: int, to_doctor_id: int):
        return self.repository.transfer_patient_assignment(patient_id, current_doctor_id, from_doctor_id, to_doctor_id)

    def get_patient_admission_history(self, patient_id: int, page: int, page_size: int):
        return self.repository.get_patient_admission_history(patient_id, page, page_size)

    def get_patient_conditions(self, patient_id: int):
        return self.repository.get_patient_conditions(patient_id)

    def assign_patient_condition(self, patient_id: int, condition_id: int, doctor_id: int):
        return self.repository.assign_patient_condition(patient_id, condition_id, doctor_id)

    def update_condition_assignment(self, assignment_id: int, doctor_id: int, status: str | None, notes: str | None):
        return self.repository.update_condition_assignment(assignment_id, doctor_id, status, notes)

    def get_patient_allergies(self, patient_id: int, page: int, page_size: int):
        return self.repository.get_patient_allergies(patient_id, page, page_size)

    def create_patient_allergy(self, patient_id: int, doctor_id: int, allergy_name: str, severity: str):
        return self.repository.create_patient_allergy(patient_id, doctor_id, allergy_name, severity)

    def update_patient_allergy(self, allergy_id: int, doctor_id: int, severity: str | None):
        return self.repository.update_patient_allergy(allergy_id, doctor_id, severity)

    def get_patient_diagnosis(self, patient_id: int, page: int, page_size: int):
        return self.repository.get_patient_diagnosis(patient_id, page, page_size)

    def create_patient_diagnosis(self, patient_id: int, doctor_id: int, diagnosis: str, notes: str | None):
        return self.repository.create_patient_diagnosis(patient_id, doctor_id, diagnosis, notes)

    def update_patient_diagnosis(
            self,
            diagnosis_id: int,
            doctor_id: int,
            status: str | None,
            note: str | None,
            notes: str | None,
    ):
        return self.repository.update_patient_diagnosis(diagnosis_id, doctor_id, status, note, notes)

    def administer_medication(
            self,
            patient_id: int,
            doctor_id: int,
            name: str,
            dosage: str,
            frequency: str,
            notes: str | None,
    ):
        return self.repository.administer_medication(patient_id, doctor_id, name, dosage, frequency, notes)

    def get_patient_medications(self, patient_id: int):
        return self.repository.get_patient_medications(patient_id)

    def update_medication(self, medication_id: int, doctor_id: int, dosage: str | None, frequency: str | None, note: str):
        return self.repository.update_medication(medication_id, doctor_id, dosage, frequency, note)

    def get_patient_activities(self, patient_id: int):
        return self.repository.get_patient_activities(patient_id)

    def get_condition_options(self):
        return self.repository.get_condition_options()
