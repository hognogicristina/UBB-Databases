from __future__ import annotations


def transfer_patient(new_department: str) -> dict:
    return {
        "new_department": new_department,
        "activity": {
            "type": "TRANSFER",
            "title": f"Transferred to {new_department}",
            "description": "Patient condition requires specialized care",
            "status": "completed",
            "scheduled_at": None,
        },
    }
