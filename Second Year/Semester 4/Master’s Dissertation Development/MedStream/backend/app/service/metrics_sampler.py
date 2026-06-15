import logging
import threading

from app.core.config import settings
from app.db.session import SessionLocal
from app.service.metrics import record_comparison_metric_sample

logger = logging.getLogger(__name__)


class MetricsSamplerController:
    def __init__(self):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        self._started = False

    def start(self):
        with self._lock:
            if self._started:
                return

            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="medstream-metrics-sampler")
            self._thread.start()
            self._started = True

    def shutdown(self):
        with self._lock:
            if not self._started:
                return

            self._stop_event.set()
            self._started = False

    def _run_loop(self):
        interval_seconds = max(1, int(settings.metrics_sample_interval_seconds or 4))
        while not self._stop_event.is_set():
            self._record_sample()
            self._stop_event.wait(interval_seconds)

    def _record_sample(self):
        try:
            with SessionLocal() as db:
                record_comparison_metric_sample(
                    db,
                    retention_hours=settings.metrics_sample_retention_hours,
                )
        except Exception:
            logger.exception("Failed to record comparison metric sample.")


metrics_sampler_controller = MetricsSamplerController()
