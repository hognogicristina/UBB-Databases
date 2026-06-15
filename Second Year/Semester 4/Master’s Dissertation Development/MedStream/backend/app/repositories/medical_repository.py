import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "helpers"


def _load_csv_column(filename, index):
    values = []
    with open(DATA_DIR / filename, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) > index:
                value = row[index].strip()
                if value:
                    values.append(value)
    return sorted(set(values))


def _load_drugs():
    rows = []
    with open(DATA_DIR / "drugs.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "medication": row["drug_name"].strip(),
                "condition": row["medical_condition"].strip(),
                "pregnancy_category": row["pregnancy_category"].strip()
            })
    return rows


def _load_conditions():
    values = set()

    with open(DATA_DIR / "drugs.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            condition = (row.get("medical_condition") or "").strip()
            if condition:
                values.add(condition)

    return sorted(values)


def _load_departments():
    values = set()

    with open(DATA_DIR / "departments.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            values.add(row["Department"].strip())

    return sorted(values)


def _load_counties():
    values = []
    with open(DATA_DIR / "counties.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            values.append(row["name"].strip())
    return values


def get_all_counties() -> list[str]:
    return _load_counties()


def get_all_departments() -> list[str]:
    return _load_departments()


def get_all_diagnoses() -> list[str]:
    return _load_csv_column("diagnosis.csv", 1)


def get_all_allergies() -> list[str]:
    return _load_csv_column("allergies.csv", 4)


def get_all_medications() -> list[dict]:
    return _load_drugs()


def get_all_conditions() -> list[str]:
    return _load_conditions()


def get_all_activity_types() -> list[str]:
    return _load_csv_column("activity_types.csv", 0)


def get_all_dosages() -> list[str]:
    return _load_csv_column("dosages.csv", 0)


def get_all_frequencies() -> list[str]:
    return _load_csv_column("frequencies.csv", 0)
