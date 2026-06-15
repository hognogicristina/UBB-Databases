from __future__ import annotations

import time

from app.simulator.buffers.buffers import SimulatorBuffers
from app.simulator.config.simulator_config import SimulatorConfig
from app.simulator.core.scheduler import BatchScheduler
from app.simulator.messaging.kafka_producer import SimulatorKafkaProducer
from app.simulator.repositories.simulator_repository import SimulatorRepository
from app.simulator.services.batch_service import BatchService
from app.simulator.services.simulator_service import SimulatorService


def run() -> None:
    config = SimulatorConfig.from_env()
    buffers = SimulatorBuffers(config=config)
    repository = SimulatorRepository()
    producer = SimulatorKafkaProducer()

    simulator_service = SimulatorService(
        config=config,
        buffers=buffers,
        repository=repository,
        producer=producer,
    )
    batch_service = BatchService(
        config=config,
        buffers=buffers,
        repository=repository,
        producer=producer,
    )

    scheduler = BatchScheduler(config=config, batch_service=batch_service)
    scheduler.start()

    simulator_service.initialize()

    while True:
        simulator_service.run_cycle()
        time.sleep(config.cycle_sleep_seconds)


if __name__ == "__main__":
    run()
