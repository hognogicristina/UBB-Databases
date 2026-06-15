from app.repositories import medical_repository

COUNTIES = medical_repository.get_all_counties()
DEPARTMENTS = medical_repository.get_all_departments()
DIAGNOSIS = medical_repository.get_all_diagnoses()
ALLERGIES = medical_repository.get_all_allergies()
DRUGS = medical_repository.get_all_medications()
CONDITIONS = medical_repository.get_all_conditions()
ACTIVITY_TYPES = medical_repository.get_all_activity_types()
DOSAGES = medical_repository.get_all_dosages()
FREQUENCIES = medical_repository.get_all_frequencies()
STATUS = ["active", "improving", "stable", "worsening", "critical", "resolved", "chronic"]
DISCHARGE = ["Recovered", "Transferred", "Stable condition"]


def load_counties():
    return medical_repository.get_all_counties()


def load_departments():
    return medical_repository.get_all_departments()


def load_drugs():
    return medical_repository.get_all_medications()


def load_conditions():
    return medical_repository.get_all_conditions()


def load_csv_column(filename, index):
    if filename == "diagnosis.csv":
        return medical_repository.get_all_diagnoses()
    if filename == "allergies.csv":
        return medical_repository.get_all_allergies()
    if filename == "activity_types.csv":
        return medical_repository.get_all_activity_types()
    if filename == "dosages.csv":
        return medical_repository.get_all_dosages()
    if filename == "frequencies.csv":
        return medical_repository.get_all_frequencies()
    raise ValueError(f"Unsupported clinical records dataset: {filename}")


__all__ = [
    "ACTIVITY_TYPES",
    "ALLERGIES",
    "CONDITIONS",
    "COUNTIES",
    "DEPARTMENTS",
    "DIAGNOSIS",
    "DISCHARGE",
    "DOSAGES",
    "DRUGS",
    "FREQUENCIES",
    "STATUS",
    "load_conditions",
    "load_counties",
    "load_csv_column",
    "load_departments",
    "load_drugs",
]
