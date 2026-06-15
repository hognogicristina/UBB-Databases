from __future__ import annotations

from app.repositories.doctor_repository import DoctorRepository


class DoctorService:
    def __init__(self, repository: DoctorRepository | None = None):
        self.repository = repository or DoctorRepository()

    def list_doctors(self):
        return self.repository.list_doctors()

    def get_current_doctor(self, authorization: str | None):
        return self.repository.get_current_doctor(authorization)

    def get_email_verification_expired(self, doctor_id: int):
        return self.repository.get_email_verification_expired(doctor_id)

    def get_doctor_activities(self, doctor_id: int):
        return self.repository.get_doctor_activities(doctor_id)

    def create_doctor_activity(self, doctor_id: int, payload, current_doctor_id: int):
        return self.repository.create_doctor_activity(doctor_id, payload, current_doctor_id)

    def update_doctor_activity(self, doctor_id: int, activity_id: int, payload, current_doctor_id: int):
        return self.repository.update_doctor_activity(doctor_id, activity_id, payload, current_doctor_id)

    def update_current_doctor(self, doctor_id: int, payload):
        return self.repository.update_current_doctor(doctor_id, payload)

    def update_current_doctor_email(self, doctor_id: int, email: str):
        return self.repository.update_current_doctor_email(doctor_id, email)

    def request_password_reset(self, payload):
        return self.repository.request_password_reset(payload)

    def request_account_recovery(self, payload):
        return self.repository.request_account_recovery(payload)

    def verify_account_recovery(self, token: str):
        return self.repository.verify_account_recovery(token)

    def confirm_password_reset(self, payload):
        return self.repository.confirm_password_reset(payload)

    def get_doctor_patients(self, doctor_id: int):
        return self.repository.get_doctor_patients(doctor_id)

    def get_available_doctors_by_department(self, department: str, exclude_doctor_id: int):
        return self.repository.get_available_doctors_by_department(department, exclude_doctor_id)

    def delete_doctor(self, doctor_id: int, current_doctor_id: int):
        return self.repository.delete_doctor(doctor_id, current_doctor_id)

    def assign_patient_to_doctor(self, doctor_id: int, patient_id: int, current_doctor_id: int):
        return self.repository.assign_patient_to_doctor(doctor_id, patient_id, current_doctor_id)

    def remove_patient_from_doctor(self, doctor_id: int, patient_id: int):
        return self.repository.remove_patient_from_doctor(doctor_id, patient_id)

    def register_doctor(self, payload):
        return self.repository.register_doctor(payload)

    def login_doctor(self, payload):
        return self.repository.login_doctor(payload)

    def verify_email(self, token: str | None):
        return self.repository.verify_email(token)

    def resend_verification_email(self, doctor_id: int | None = None, token: str | None = None):
        return self.repository.resend_verification_email(doctor_id, token)
