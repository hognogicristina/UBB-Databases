from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.utils.datetime import now_utc


class ComparisonMetricSample(Base):
    __tablename__ = "comparison_metric_samples"
    __table_args__ = (
        Index("ix_comparison_metric_samples_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=now_utc)
    streaming_alerts_per_minute: Mapped[int] = mapped_column(Integer, default=0)
    batch_alerts_per_minute: Mapped[float | None] = mapped_column(Float, nullable=True)
    streaming_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    batch_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    batch_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    has_batch_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
