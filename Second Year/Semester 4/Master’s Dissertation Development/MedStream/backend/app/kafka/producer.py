import json

from confluent_kafka import KafkaException, Producer

from app.kafka.config import get_kafka_config

producer = Producer(get_kafka_config())


def send_message(topic: str, payload: dict):
    try:
        producer.produce(topic, json.dumps(payload).encode("utf-8"))
        producer.poll(0)
        producer.flush(0.1)
    except (BufferError, KafkaException) as error:
        print(f"Kafka producer unavailable, dropping {topic} message: {error}")
