#!/bin/bash
# Create required Kafka topics

echo "🔧 Creating Kafka topics..."

cd "$(dirname "$0")/.."

# Create topics using kafka-topics command in the Kafka container
docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic anchors.write \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic anchors.indexed \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic recall.request \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic recall.response \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic retell.response \
  --partitions 1 \
  --replication-factor 1

echo ""
echo "✅ Topics created! Listing all topics:"
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

