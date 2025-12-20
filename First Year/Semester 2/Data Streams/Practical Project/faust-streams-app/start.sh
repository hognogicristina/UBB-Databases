#!/bin/bash

set -e

echo "Stopping any existing Kafka instance..."
docker compose down -v

echo "Deleting local Faust data..."
rm -rf sensor-stream-app-data/

echo "Starting Zookeeper and Kafka..."
docker compose up -d

echo "Waiting for Kafka to be ready..."
until docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 --list &>/dev/null; do
  echo "Kafka is not ready yet. Waiting..."
  sleep 3
done

echo "Kafka is ready."

echo "Creating required Kafka topics..."
TOPICS=(
  "temperature-readings"
  "co2-readings"
  "motion-readings"
  "light-readings"
  "sound-readings"
  "occupancy-readings"
  "sensor-stream-app-temp_avg-changelog"
  "sensor-stream-app-latest_temp-changelog"
  "sensor-stream-app-latest_motion-changelog"
)

for topic in "${TOPICS[@]}"; do
  docker compose exec kafka kafka-topics --bootstrap-server localhost:9092 \
    --create --if-not-exists --topic "$topic" --partitions 1 --replication-factor 1
done

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting Faust..."
faust -A app worker -l info &
FAUST_PID=$!

echo "Starting the producer with real data..."
python producer.py

wait $FAUST_PID