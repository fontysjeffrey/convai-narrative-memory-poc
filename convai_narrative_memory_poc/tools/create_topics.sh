#!/bin/bash
# Create required Kafka topics and ensure Qdrant collection is clean.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "🧼 Resetting Qdrant collection before demo..."
docker compose run --rm tools python - <<'PY'
from convai_narrative_memory_poc.workers.common.utils import get_embedding_dim, QDRANT_URL, QDRANT_COLLECTION
from qdrant_client import QdrantClient

client = QdrantClient(url=QDRANT_URL)
dim = get_embedding_dim()
try:
    client.delete_collection(QDRANT_COLLECTION)
except Exception:
    pass
client.recreate_collection(
    collection_name=QDRANT_COLLECTION,
    vectors_config={"size": dim, "distance": "Cosine"},
)
PY

echo "🔧 Creating Kafka topics (anchors-write, recall-request, recall-response, retell-response, anchors-indexed)..."

# Create topics using kafka-topics command in the Kafka container
docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic anchors-write \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic anchors-indexed \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic recall-request \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic recall-response \
  --partitions 1 \
  --replication-factor 1

docker compose exec kafka kafka-topics --create --if-not-exists \
  --bootstrap-server localhost:9092 \
  --topic retell-response \
  --partitions 1 \
  --replication-factor 1

echo ""
echo "✅ Topics created! Listing all topics:"
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

