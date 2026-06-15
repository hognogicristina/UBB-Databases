import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.batch.status import batch_status_store, utc_now

BATCH_INTERVAL_SECONDS = 30


class BatchRuntimeController:
    def __init__(self):
        self._lock = threading.Lock()
        self._interval_seconds = BATCH_INTERVAL_SECONDS
        self._cron_expression = None
        self._job_callback = None
        self._job_lock = threading.Lock()
        self._scheduler = BackgroundScheduler(timezone="Europe/Bucharest")
        self._started = False

    def start(self, job_callback, interval_seconds: int | None = None):
        with self._lock:
            self._job_callback = job_callback
            self._interval_seconds = max(1, int(interval_seconds or BATCH_INTERVAL_SECONDS))
            self._cron_expression = None
            if not self._started:
                self._scheduler.start()
                self._started = True
            self._schedule_current_job()

    def shutdown(self):
        with self._lock:
            if self._started:
                self._scheduler.shutdown(wait=False)
                self._started = False

    def interval_seconds(self):
        with self._lock:
            return self._interval_seconds

    def cron_expression(self):
        with self._lock:
            return self._cron_expression

    def configure_interval(self, interval_seconds: int):
        with self._lock:
            self._cron_expression = None
            self._interval_seconds = max(1, int(interval_seconds))
            self._schedule_current_job()

    def configure_cron(self, cron_expression: str):
        with self._lock:
            self._cron_expression = cron_expression
            self._schedule_current_job()

    def next_run_time(self):
        with self._lock:
            return self._current_next_run_time()

    def request_run(self):
        thread = threading.Thread(target=self._run_job, daemon=True, name="medstream-batch-manual")
        thread.start()

    def _schedule_current_job(self):
        trigger = (
            CronTrigger.from_crontab(self._cron_expression, timezone="Europe/Bucharest")
            if self._cron_expression
            else IntervalTrigger(seconds=self._interval_seconds, timezone="Europe/Bucharest")
        )
        self._scheduler.add_job(
            self._run_job,
            trigger=trigger,
            id="medstream-batch",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        batch_status_store.configure(
            self._interval_seconds,
            self._current_next_run_time(),
            self._cron_expression,
        )

    def _run_job(self):
        if self._job_callback is None:
            return

        if not self._job_lock.acquire(blocking=False):
            return

        try:
            self._job_callback()
        finally:
            with self._lock:
                batch_status_store.configure(
                    self._interval_seconds,
                    self._current_next_run_time(),
                    self._cron_expression,
                )
            self._job_lock.release()

    def _current_next_run_time(self):
        job = self._scheduler.get_job("medstream-batch")
        if job is None or job.next_run_time is None:
            return None
        return job.next_run_time.astimezone(utc_now().tzinfo)


batch_runtime_controller = BatchRuntimeController()
