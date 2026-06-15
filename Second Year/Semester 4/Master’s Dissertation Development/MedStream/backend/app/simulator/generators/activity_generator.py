from __future__ import annotations

import random
from datetime import timedelta

from app.utils.datetime import now_utc


def generate_activity(type_name: str, source: str, reference_time=None) -> dict:
    base_time = reference_time or now_utc()
    if type_name == "Consultation":
        title = f"Consultation - {source}"
        description = f"Patient evaluated due to {source}"
    elif type_name == "Surgery":
        title = f"Surgery - {source}"
        description = f"Surgical intervention required for {source}"
    elif type_name == "Procedure":
        title = f"Procedure - {source}"
        description = f"Medical procedure performed because of {source}"
    elif type_name == "Transfer":
        title = f"Transfer - {source}"
        description = f"Patient transferred due to {source}"
    elif type_name == "Lab test":
        title = f"Lab Test - {source}"
        description = f"Lab investigation requested for {source}"
    else:
        title = f"Imaging - {source}"
        description = f"Imaging required to assess {source}"

    return {
        "type": type_name,
        "title": title,
        "description": description,
        "status": "incoming",
        "scheduled_at": base_time + timedelta(hours=random.randint(1, 24)),
    }
