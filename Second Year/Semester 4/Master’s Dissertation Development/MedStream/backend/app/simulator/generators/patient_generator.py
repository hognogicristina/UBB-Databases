from __future__ import annotations

import random
from datetime import date

from faker import Faker

fake = Faker("ro_RO")


def generate_cnp(birth_date: date, gender: str, index: int) -> str:
    if birth_date.year >= 2000:
        sex_code = "5" if gender == "male" else "6"
    else:
        sex_code = "1" if gender == "male" else "2"

    yy = birth_date.strftime("%y")
    mm = birth_date.strftime("%m")
    dd = birth_date.strftime("%d")

    county = f"{random.randint(1, 41):02d}"
    serial = f"{index % 999:03d}"

    partial = f"{sex_code}{yy}{mm}{dd}{county}{serial}"

    control_key = "279146358279"
    checksum = sum(int(digit) * int(weight) for digit, weight in zip(partial, control_key)) % 11
    checksum = 1 if checksum == 10 else checksum

    return f"{partial}{checksum}"


def generate_phone_candidate() -> str:
    return f"+407{random.randint(1000000, 9999999)}"


def generate_address(counties: list[str]) -> dict:
    return {
        "street": fake.street_name(),
        "number": str(random.randint(1, 200)),
        "apartment": None,
        "city": fake.city(),
        "county": random.choice(counties),
        "postal_code": f"{random.randint(100000, 999999)}",
        "country": "Romania",
    }


def choose_medication_profile(drugs: list[dict], is_pregnant: bool) -> dict | None:
    allowed_categories = ["A", "B"] if is_pregnant else ["A", "B", "C", "D", "N"]
    valid_drugs = [drug for drug in drugs if drug["pregnancy_category"] in allowed_categories]
    if not valid_drugs:
        return None

    medications_by_condition: dict[str, set[str]] = {}
    for drug in valid_drugs:
        condition = (drug.get("condition") or "").strip()
        medication = (drug.get("medication") or "").strip()
        if not condition or not medication:
            continue
        medications_by_condition.setdefault(condition, set()).add(medication)

    if not medications_by_condition:
        return None

    selected_condition = random.choice(sorted(medications_by_condition.keys()))
    medication_options = sorted(medications_by_condition[selected_condition])
    selected_medication = medication_options[0]
    return {
        "medication_name": selected_medication,
        "condition_name": selected_condition,
        "medication_options": medication_options,
    }


def generate_patient_identity(index: int, department: str) -> dict:
    gender = random.choice(["male", "female"])
    birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90)
    is_pregnant = False

    if gender == "female" and 18 <= (date.today().year - birth_date.year) <= 45:
        is_pregnant = random.random() < 0.2

    return {
        "first_name": fake.first_name_male() if gender == "male" else fake.first_name_female(),
        "last_name": fake.last_name(),
        "gender": gender,
        "department": department,
        "birth_date": birth_date,
        "cnp": generate_cnp(birth_date, gender, index),
        "is_discharged": False,
        "is_pregnant": is_pregnant,
    }


def generate_patient_profile(
        *,
        base_condition: str,
        diagnosis_seed: str | None,
        all_conditions: list[str],
        all_diagnoses: list[str],
        all_allergies: list[str],
        dosages: list[str],
        frequencies: list[str],
) -> dict:
    target_condition_count = random.randint(2, 5)
    selected_conditions: list[str] = []

    for candidate in [base_condition, diagnosis_seed]:
        if candidate and candidate not in selected_conditions:
            selected_conditions.append(candidate)

    extra_conditions = [condition for condition in all_conditions if condition]
    random.shuffle(extra_conditions)
    for candidate in extra_conditions:
        if len(selected_conditions) >= target_condition_count:
            break
        if candidate not in selected_conditions:
            selected_conditions.append(candidate)

    target_diagnosis_count = random.randint(1, 3)
    selected_diagnoses: list[str] = []
    if diagnosis_seed:
        selected_diagnoses.append(diagnosis_seed)

    diagnosis_candidates = [item for item in all_diagnoses if item]
    random.shuffle(diagnosis_candidates)
    for candidate in diagnosis_candidates:
        if len(selected_diagnoses) >= target_diagnosis_count:
            break
        if candidate not in selected_diagnoses:
            selected_diagnoses.append(candidate)

    allergy_candidates = [item for item in all_allergies if item]
    allergy_count = min(random.randint(1, 4), len(allergy_candidates))
    selected_allergies = random.sample(allergy_candidates, k=allergy_count) if allergy_count > 0 else []

    return {
        "conditions": selected_conditions,
        "diagnoses": selected_diagnoses,
        "allergies": selected_allergies,
        "dosage": f"{random.choice(['1', '2'])}x {random.choice(dosages)}",
        "frequency": random.choice(frequencies),
    }
