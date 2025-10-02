import os, json, sys, math, datetime as dt
from confluent_kafka import Consumer, Producer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from workers.common.utils import (
    QDRANT_URL,
    QDRANT_COLLECTION,
    KAFKA_BOOTSTRAP,
    human_age,
)

TOP_IN = "recall.request"
TOP_OUT = "recall.response"

LAM = 0.002  # time decay per day
MU = 0.001  # cross-time damping


def search_anchors(client, query_vec, top_k=5):
    res = client.search(
        QDRANT_COLLECTION, query_vector=query_vec, limit=top_k, with_payload=True
    )
    return res


def deterministic_query_vec(text: str):
    from workers.common.utils import deterministic_embed

    return deterministic_embed(text)


def decay_weight(stored_at_iso: str, now: dt.datetime) -> float:
    stored = dt.datetime.fromisoformat(stored_at_iso.replace("Z", "+00:00")).replace(
        tzinfo=None
    )
    age_days = (now - stored).days
    return math.exp(-LAM * max(age_days, 0))


def main():
    client = QdrantClient(url=QDRANT_URL)
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP,
            "group.id": "resonance",
            "auto.offset.reset": "earliest",
        }
    )
    producer = Producer({"bootstrap.servers": KAFKA_BOOTSTRAP})
    consumer.subscribe([TOP_IN])
    print("[resonance] listening...")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print(f"[resonance] error: {msg.error()}", file=sys.stderr)
            continue
        try:
            payload = json.loads(msg.value().decode("utf-8"))
            request_id = payload["request_id"]
            query = payload["query"]
            top_k = int(payload.get("top_k", 5))
            assumed_age = payload.get(
                "assume_anchor_age"
            )  # optional ISO 8601 duration, not used here
            now_iso = payload.get("now")
            now = (
                dt.datetime.fromisoformat(now_iso.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
                if now_iso
                else dt.datetime.now(dt.timezone.utc)
            )

            qvec = deterministic_query_vec(query)
            hits = search_anchors(client, qvec, top_k=top_k)
            # Simple activation = similarity * decay * salience
            scored = []
            for h in hits:
                pl = h.payload
                decay = decay_weight(pl["stored_at"], now)
                sal = float(pl.get("salience", 1.0))
                act = float(h.score) * decay * sal
                scored.append((act, h))

            scored.sort(key=lambda x: x[0], reverse=True)
            beats = []
            for act, h in scored[:3]:
                pl = h.payload
                stored = dt.datetime.fromisoformat(
                    pl["stored_at"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
                beats.append(
                    {
                        "anchor_id": h.id,
                        "text": pl["text"],
                        "perceived_age": human_age(now - stored),
                        "activation": act,
                    }
                )
            out = {"request_id": request_id, "beats": beats}
            producer.produce(TOP_OUT, json.dumps(out).encode("utf-8"))
            producer.flush()
            print(f"[resonance] replied {request_id} with {len(beats)} beats")
        except Exception as e:
            print(f"[resonance] exception: {e}", file=sys.stderr)
    consumer.close()


if __name__ == "__main__":
    main()
