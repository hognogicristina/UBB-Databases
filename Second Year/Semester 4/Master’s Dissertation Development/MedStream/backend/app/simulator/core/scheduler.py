from __future__ import annotations

import threading
import time

from app.simulator.config.simulator_config import SimulatorConfig
from app.simulator.services.batch_service import BatchService


class BatchScheduler:
    def __init__(self, *, config: SimulatorConfig, batch_service: BatchService):
        self.config = config
        self.batch_service = batch_service
        self._started = False
        self._lock = threading.Lock()

    def start(self) -> None:
        with self._lock:
            if self._started:
                return

            thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="medstream-simulator-batch-scheduler",
            )
            thread.start()
            self._started = True

    def _run_loop(self) -> None:
        while True:
            time.sleep(self.config.batch_interval_seconds)
            try:
                self.batch_service.run_batch_analytics_job()
            except Exception as error:
                print("Batch scheduler error:", error)
