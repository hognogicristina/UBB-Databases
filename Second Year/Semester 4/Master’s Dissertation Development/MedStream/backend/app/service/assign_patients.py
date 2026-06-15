from app.repositories.patient_repository import PatientRepository

_patient_repository = PatientRepository()


def assign_doctor_to_patient(db, doctor_id, patient_id):
    _patient_repository.assign_doctor_to_patient_with_session(db, doctor_id, patient_id)
