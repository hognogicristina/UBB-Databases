from app.core.config import settings


def get_kafka_config():
    return {
        "bootstrap.servers": settings.kafka_bootstrap_servers
    }
