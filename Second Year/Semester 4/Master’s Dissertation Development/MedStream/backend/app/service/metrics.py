from app.repositories.metrics_repository import (
    WINDOW_DELTA,
    WINDOW_MINUTES,
    get_batch_insights_repo,
    get_batch_alerts_history,
    get_comparison_history,
    get_comparison_metrics,
    get_latest_batch_analytics,
    get_latest_batch_metrics,
    paginate_items,
    record_comparison_metric_sample,
    refresh_batch_snapshot,
    streaming_metrics_store,
)


def get_batch_insights_service(db, *, departments_page: int, diagnoses_page: int, page_size: int):
    return get_batch_insights_repo(
        db,
        departments_page=departments_page,
        diagnoses_page=diagnoses_page,
        page_size=page_size,
    )


__all__ = [
    "WINDOW_DELTA",
    "WINDOW_MINUTES",
    "get_batch_insights_service",
    "get_batch_alerts_history",
    "get_comparison_history",
    "get_comparison_metrics",
    "get_latest_batch_analytics",
    "get_latest_batch_metrics",
    "paginate_items",
    "record_comparison_metric_sample",
    "refresh_batch_snapshot",
    "streaming_metrics_store",
]
