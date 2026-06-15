from threading import Lock

from app.utils.datetime import now_utc, to_utc


class BatchStatusStore:
    def __init__(self):
        self._lock = Lock()
        self._status = {
            "interval_seconds": 30,
            "last_run_started_at": None,
            "last_successful_run_at": None,
            "last_run_finished_at": None,
            "next_run_estimate": None,
            "last_run_status": "idle",
            "last_run_error": None,
            "last_run_duration_ms": None,
            "is_running": False,
            "progress": 0,
            "last_run": None,
            "stage": "Idle",
            "cron_expression": None,
        }

    def configure(self, interval_seconds, next_run_estimate=None, cron_expression=None):
        with self._lock:
            self._status["interval_seconds"] = interval_seconds
            self._status["next_run_estimate"] = next_run_estimate
            self._status["cron_expression"] = cron_expression

    def mark_started(self, started_at, next_run_estimate=None, stage="Loading data"):
        with self._lock:
            self._status["last_run_started_at"] = started_at
            self._status["last_run_status"] = "running"
            self._status["last_run_error"] = None
            self._status["next_run_estimate"] = next_run_estimate
            self._status["is_running"] = True
            self._status["progress"] = 0
            self._status["stage"] = stage

    def mark_progress(self, progress, stage=None):
        with self._lock:
            self._status["progress"] = max(0, min(100, int(progress)))
            if stage:
                self._status["stage"] = stage

    def mark_success(self, finished_at, next_run_estimate, duration_ms=None):
        with self._lock:
            self._status["last_successful_run_at"] = finished_at
            self._status["last_run_finished_at"] = finished_at
            self._status["last_run_status"] = "success"
            self._status["last_run_error"] = None
            self._status["next_run_estimate"] = next_run_estimate
            self._status["last_run_duration_ms"] = duration_ms
            self._status["is_running"] = False
            self._status["progress"] = 100
            self._status["last_run"] = finished_at
            self._status["stage"] = "Completed"

    def mark_failure(self, finished_at, error, next_run_estimate, duration_ms=None):
        with self._lock:
            self._status["last_run_finished_at"] = finished_at
            self._status["last_run_status"] = "failed"
            self._status["last_run_error"] = str(error)
            self._status["next_run_estimate"] = next_run_estimate
            self._status["last_run_duration_ms"] = duration_ms
            self._status["is_running"] = False
            self._status["progress"] = 100
            self._status["last_run"] = finished_at
            self._status["stage"] = "Failed"

    def snapshot(self):
        with self._lock:
            snapshot = dict(self._status)
            for key in (
                    "last_run_started_at",
                    "last_successful_run_at",
                    "last_run_finished_at",
                    "next_run_estimate",
                    "last_run",
            ):
                snapshot[key] = to_utc(snapshot.get(key))

            next_run_estimate = snapshot.get("next_run_estimate")
            if next_run_estimate:
                snapshot["next_run_in_seconds"] = max(
                    0,
                    int((next_run_estimate - utc_now()).total_seconds()),
                )
            else:
                snapshot["next_run_in_seconds"] = None
            return snapshot


batch_status_store = BatchStatusStore()


def utc_now():
    return now_utc()
