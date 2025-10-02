import os, json, time, sys, datetime as dt
from confluent_kafka import Consumer, Producer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from common.utils import QDRANT_URL, QDRANT_COLLECTION, KAFKA_BOOTSTRAP, deterministic_embed

TOP_IN = "anchors.write"
TOP_OUT = "anchors.indexed"

def ensure_collection(client: QdrantClient):
    cols = client.get_collections().collections
    names = [c.name for c in cols]
    if QDRANT_COLLECTION not in names:
        client.recreate_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE),
        )

def main():
    client = QdrantClient(url=QDRANT_URL)
    ensure_collection(client)
    consumer = Consumer({'bootstrap.servers': KAFKA_BOOTSTRAP,
                         'group.id': 'indexer', 'auto.offset.reset':'earliest'})
    producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP})
    consumer.subscribe([TOP_IN])
    print("[indexer] listening...")
    while True:
        msg = consumer.poll(1.0)
        if msg is None: 
            continue
        if msg.error():
            print(f"[indexer] error: {msg.error()}", file=sys.stderr); continue
        try:
            payload = json.loads(msg.value().decode('utf-8'))
            anchor_id = payload.get("anchor_id")
            text = payload["text"]
            stored_at = payload["stored_at"]
            meta = payload.get("meta", {})
            salience = float(payload.get("salience", 1.0))
            embedding = deterministic_embed(text)
            client.upsert(
                collection_name=QDRANT_COLLECTION,
                wait=True,
                points=[models.PointStruct(
                    id=anchor_id,
                    vector=embedding,
                    payload={
                        "text": text,
                        "stored_at": stored_at,
                        "salience": salience,
                        "meta": meta
                    }
                )]
            )
            out = {"anchor_id": anchor_id, "ok": True}
            producer.produce(TOP_OUT, json.dumps(out).encode('utf-8'))
            producer.flush()
            print(f"[indexer] indexed {anchor_id}")
        except Exception as e:
            print(f"[indexer] exception: {e}", file=sys.stderr)
    consumer.close()

if __name__ == "__main__":
    main()
