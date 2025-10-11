#!/bin/bash
# Quick script to check if all workers are running

echo "🔍 Checking Kafka Stack Status..."
echo ""

cd "$(dirname "$0")/.."

echo "📊 Docker Compose Services:"
docker compose ps

echo ""
echo "🔥 Recent Worker Logs:"
echo ""
echo "=== Indexer ==="
docker compose logs --tail=3 indexer 2>/dev/null || echo "Not running"
echo ""
echo "=== Resonance ==="
docker compose logs --tail=3 resonance 2>/dev/null || echo "Not running"
echo ""
echo "=== Reteller ==="
docker compose logs --tail=3 reteller 2>/dev/null || echo "Not running"

