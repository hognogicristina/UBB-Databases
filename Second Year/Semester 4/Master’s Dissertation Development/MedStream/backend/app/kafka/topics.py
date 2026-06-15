from confluent_kafka import KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from app.core.config import settings


def ensure_topics() -> bool:
    admin = AdminClient({"bootstrap.servers": settings.kafka_bootstrap_servers})
    try:
        metadata = admin.list_topics(timeout=10)
    except KafkaException as error:
        print(f"Kafka topics unavailable, continuing startup without topic verification: {error}")
        return False

    existing_topics = set(metadata.topics.keys())
    required_topics = [
        settings.kafka_vitals_topic,
        settings.kafka_alerts_topic,
        settings.kafka_batch_topic,
    ]
    missing_topics = [
        NewTopic(topic, num_partitions=1, replication_factor=1)
        for topic in required_topics
        if topic not in existing_topics
    ]

    if not missing_topics:
        return True

    futures = admin.create_topics(missing_topics)

    for topic, future in futures.items():
        try:
            future.result()
            print(f"Created Kafka topic: {topic}")
        except Exception as e:
            if "TOPIC_ALREADY_EXISTS" in str(e):
                continue
            print(f"Kafka topic {topic} could not be created, continuing startup: {e}")
            return False

    return True
