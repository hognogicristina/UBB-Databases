from fastapi import APIRouter, HTTPException

from app.batch.runtime import batch_runtime_controller
from app.batch.status import batch_status_store
from app.core.http import ApiResponse, success_response
from app.schemas.stats import BatchJobStatusRead, BatchProgressRead, BatchScheduleRead, BatchScheduleUpdate

router = APIRouter(prefix="/batch", tags=["batch"])
WEEKDAY_MAP = {
    "MONDAY": "MON",
    "TUESDAY": "TUE",
    "WEDNESDAY": "WED",
    "THURSDAY": "THU",
    "FRIDAY": "FRI",
    "SATURDAY": "SAT",
    "SUNDAY": "SUN",
}
CRON_DAY_TO_FULL = {
    "MON": "MONDAY",
    "TUE": "TUESDAY",
    "WED": "WEDNESDAY",
    "THU": "THURSDAY",
    "FRI": "FRIDAY",
    "SAT": "SATURDAY",
    "SUN": "SUNDAY",
}


def _parse_time_parts(value: str | None):
    if not value or ":" not in value:
        raise HTTPException(status_code=400, detail="Time must be provided in HH:MM format.")

    hour_text, minute_text = value.split(":", 1)

    if not (hour_text.isdigit() and minute_text.isdigit()):
        raise HTTPException(status_code=400, detail="Time must be provided in HH:MM format.")

    hour = int(hour_text)
    minute = int(minute_text)

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise HTTPException(status_code=400, detail="Time must be provided in HH:MM format.")

    return hour, minute


def _parse_schedule_from_snapshot(snapshot: dict) -> BatchScheduleRead:
    cron_expression = (snapshot.get("cron_expression") or "").strip()
    interval_seconds = int(snapshot.get("interval_seconds") or 0)

    if not cron_expression:
        if interval_seconds < 60:
            return BatchScheduleRead(
                type="seconds",
                value=interval_seconds,
                interval_seconds=interval_seconds,
            )

        if interval_seconds >= 3600 and interval_seconds % 3600 == 0:
            return BatchScheduleRead(
                type="hours",
                value=interval_seconds // 3600,
                interval_seconds=interval_seconds,
            )

        return BatchScheduleRead(
            type="minutes",
            value=max(1, interval_seconds // 60),
            interval_seconds=interval_seconds,
        )

    parts = cron_expression.split()
    if len(parts) == 5:
        minute, hour, day_of_month, month, day_of_week = parts
        time_value = f"{int(hour):02d}:{int(minute):02d}" if hour.isdigit() and minute.isdigit() else None

        if day_of_month == "*" and month == "*" and day_of_week == "*":
            return BatchScheduleRead(
                type="daily",
                time=time_value,
                cron_expression=cron_expression,
                interval_seconds=interval_seconds,
            )

        if day_of_month == "*" and month == "*" and day_of_week != "*":
            mapped_days = [
                CRON_DAY_TO_FULL.get(item.strip().upper(), item.strip().upper())
                for item in day_of_week.split(",")
            ]
            return BatchScheduleRead(
                type="weekly",
                time=time_value,
                days=mapped_days,
                cron_expression=cron_expression,
                interval_seconds=interval_seconds,
            )

    return BatchScheduleRead(
        type="custom",
        cron_expression=cron_expression,
        interval_seconds=interval_seconds,
    )


@router.get("/status", response_model=ApiResponse[BatchProgressRead])
def get_batch_status():
    snapshot = batch_status_store.snapshot()
    return success_response(
        "Batch progress retrieved successfully.",
        BatchProgressRead.model_validate({
            "is_running": snapshot["is_running"],
            "progress": snapshot["progress"],
            "stage": snapshot["stage"],
            "last_run": snapshot["last_run"],
            "last_run_status": snapshot["last_run_status"],
            "next_run_in_seconds": snapshot["next_run_in_seconds"],
        }).model_dump(mode="json"),
    )


@router.get("/schedule", response_model=ApiResponse[BatchScheduleRead])
def get_batch_schedule():
    snapshot = batch_status_store.snapshot()
    schedule_payload = _parse_schedule_from_snapshot(snapshot)
    return success_response(
        "Batch schedule retrieved successfully.",
        schedule_payload.model_dump(mode="json"),
    )


@router.post("/schedule", response_model=ApiResponse[BatchJobStatusRead])
def update_batch_schedule(payload: BatchScheduleUpdate):
    schedule_type = (payload.type or "").strip().lower()

    if schedule_type == "seconds":
        if payload.value is None:
            raise HTTPException(status_code=400, detail="Seconds value is required.")
        batch_runtime_controller.configure_interval(payload.value)
    elif schedule_type == "minutes":
        if payload.value is None:
            raise HTTPException(status_code=400, detail="Minutes value is required.")
        batch_runtime_controller.configure_interval(payload.value * 60)
    elif schedule_type == "hours":
        if payload.value is None:
            raise HTTPException(status_code=400, detail="Hours value is required.")
        batch_runtime_controller.configure_interval(payload.value * 3600)
    elif schedule_type == "daily":
        hour, minute = _parse_time_parts(payload.time)
        batch_runtime_controller.configure_cron(f"{minute} {hour} * * *")
    elif schedule_type == "weekly":
        hour, minute = _parse_time_parts(payload.time)
        days = payload.days or []
        mapped_days = []

        for day in days:
            day_key = day.strip().upper()
            if day_key not in WEEKDAY_MAP:
                raise HTTPException(status_code=400, detail="Weekly days must be valid weekday names.")
            mapped_days.append(WEEKDAY_MAP[day_key])

        if not mapped_days:
            raise HTTPException(status_code=400, detail="At least one weekday is required for weekly scheduling.")

        batch_runtime_controller.configure_cron(f"{minute} {hour} * * {','.join(mapped_days)}")
    elif schedule_type == "custom":
        if not payload.cron_expression:
            raise HTTPException(status_code=400, detail="Cron expression is required for custom scheduling.")
        try:
            batch_runtime_controller.configure_cron(payload.cron_expression)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Cron expression is invalid.") from error
    else:
        raise HTTPException(status_code=400, detail="Schedule type is invalid.")

    return success_response(
        "Batch schedule updated successfully.",
        BatchJobStatusRead.model_validate(batch_status_store.snapshot()).model_dump(mode="json"),
    )


@router.post("/run", response_model=ApiResponse[BatchJobStatusRead])
def run_batch_now():
    batch_runtime_controller.request_run()

    return success_response(
        "Batch run requested successfully.",
        BatchJobStatusRead.model_validate(batch_status_store.snapshot()).model_dump(mode="json"),
    )
