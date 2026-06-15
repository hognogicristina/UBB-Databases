from __future__ import annotations

import random
from datetime import date

from faker import Faker

fake = Faker("ro_RO")


def generate_doctor_payloads(
        *,
        count: int,
        departments: list[str],
        password_hash: str,
        email_prefix: str = "sim.doctor",
) -> list[dict]:
    payloads: list[dict] = []
    for index in range(max(0, count)):
        dept = departments[index % len(departments)]
        ordinal = index + 1
        payloads.append(
            {
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": f"{email_prefix}.{ordinal:03d}@med.local",
                "password_hash": password_hash,
                "specialization": dept,
                "license_number": f"SIM-LIC-{ordinal:05d}",
                "phone_number": f"+4075{ordinal:06d}",
                "birth_date": fake.date_of_birth(minimum_age=30, maximum_age=65),
            }
        )

    return payloads
