from datetime import datetime

from fastapi import APIRouter, Query

from app.core.http import ApiResponse, success_response
from app.db.session import SessionLocal
from app.schemas.stats import (
    BatchAlertsHistoryPointRead,
    ComparisonHistoryRead,
    BatchInsightsRead,
    ComparisonMetricsRead,
    ComparisonSummaryRead,
    PaginatedStreamingAlertsRead,
)
from app.service.metrics import (
    get_batch_alerts_history,
    get_batch_insights_service,
    get_comparison_history,
    get_comparison_metrics,
    get_latest_batch_metrics,
    record_comparison_metric_sample,
    streaming_metrics_store,
)

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/streaming", response_model=ApiResponse[ComparisonMetricsRead])
def get_streaming_metrics():
    streaming_metrics = streaming_metrics_store.snapshot()

    return success_response(
        "Streaming metrics retrieved successfully.",
        {
            "avg_heart_rate": streaming_metrics["avg_heart_rate"],
            "avg_oxygen": streaming_metrics["avg_oxygen"],
            "avg_temperature": streaming_metrics["avg_temperature"],
            "avg_systolic_bp": None,
            "avg_diastolic_bp": None,
            "alerts": streaming_metrics["total_alerts"],
            "execution_time_ms": streaming_metrics["execution_time_ms"],
            "recent_vitals": streaming_metrics["recent_vitals"],
        },
    )


@router.get("/batch", response_model=ApiResponse[ComparisonMetricsRead])
def get_batch_metrics():
    with SessionLocal() as db:
        batch_metrics = get_latest_batch_metrics(db)

    return success_response(
        "Batch metrics retrieved successfully.",
        {
            "avg_heart_rate": batch_metrics["avg_heart_rate"],
            "avg_oxygen": batch_metrics["avg_oxygen"],
            "avg_temperature": batch_metrics["avg_temperature"],
            "avg_systolic_bp": batch_metrics["avg_systolic_bp"],
            "avg_diastolic_bp": batch_metrics["avg_diastolic_bp"],
            "alerts": batch_metrics["total_alerts"],
            "patients_count": batch_metrics["active_patients"],
            "timestamp": batch_metrics["timestamp"],
            "execution_time_ms": batch_metrics["execution_time_ms"],
            "generated_discharge_summaries_count": batch_metrics["generated_discharge_summaries_count"],
            "pending_discharge_summaries_count": batch_metrics["pending_discharge_summaries_count"],
        },
    )


@router.get("/batch-insights", response_model=ApiResponse[BatchInsightsRead])
def get_batch_insights_endpoint(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=5, ge=1, le=50),
        departments_page: int | None = Query(default=None, ge=1),
        diagnoses_page: int | None = Query(default=None, ge=1),
):
    current_departments_page = departments_page or page
    current_diagnoses_page = diagnoses_page or page
    with SessionLocal() as db:
        insights = get_batch_insights_service(
            db,
            departments_page=current_departments_page,
            diagnoses_page=current_diagnoses_page,
            page_size=page_size,
        )

    return success_response(
        "Batch insights retrieved successfully.",
        {
            "patients_per_department": insights["patients_per_department"],
            "top_diagnosis": insights["top_diagnosis"],
            "treatment_effectiveness": insights["treatment_effectiveness"],
            "medication_effectiveness": insights["medication_effectiveness"],
        },
    )


@router.get("/streaming-alerts", response_model=ApiResponse[PaginatedStreamingAlertsRead])
def get_streaming_alerts(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=3, ge=1, le=10),
):
    return success_response(
        "Streaming alerts retrieved successfully.",
        streaming_metrics_store.alerts_snapshot(page, page_size),
    )


@router.get("/comparison", response_model=ApiResponse[ComparisonSummaryRead])
def get_metrics_comparison():
    with SessionLocal() as db:
        comparison = get_comparison_metrics(db)

    return success_response(
        "Comparison metrics retrieved successfully.",
        comparison,
    )


@router.get("/comparison-history", response_model=ApiResponse[ComparisonHistoryRead])
def get_metrics_comparison_history(
        seconds: int = Query(default=3600, ge=60, le=157680000),
        interval_seconds: int = Query(default=4, ge=1, le=604800),
        start_time: datetime | None = Query(default=None),
        end_time: datetime | None = Query(default=None),
):
    with SessionLocal() as db:
        record_comparison_metric_sample(db)
        history = get_comparison_history(
            db,
            seconds=seconds,
            interval_seconds=interval_seconds,
            start_time=start_time,
            end_time=end_time,
        )

    return success_response(
        "Comparison history retrieved successfully.",
        history,
    )


@router.get("/batch-alerts-history", response_model=ApiResponse[list[BatchAlertsHistoryPointRead]])
def get_batch_alerts_history_endpoint(limit: int = Query(default=24, ge=2, le=120)):
    with SessionLocal() as db:
        history = get_batch_alerts_history(db, limit=limit)

    return success_response(
        "Batch alerts history retrieved successfully.",
        history,
    )
