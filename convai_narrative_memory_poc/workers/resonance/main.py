import os, json, sys, math, datetime as dt
from confluent_kafka import Consumer, Producer
from qdrant_client import QdrantClient
from qdrant_client.http import models
from convai_narrative_memory_poc.workers.common.utils import (
    QDRANT_URL,
    QDRANT_COLLECTION,
    KAFKA_BOOTSTRAP,
    human_age,
    get_embedding,
)

TOP_IN = "recall.request"
TOP_OUT = "recall.response"

LAM = 0.002  # time decay per day
MU = 0.001  # cross-time damping
MAX_BEATS = int(os.getenv("RESONANCE_MAX_BEATS", "3"))
DIVERSITY_THRESHOLD = float(os.getenv("RESONANCE_DIVERSITY_THRESHOLD", "0.92"))


def search_anchors(client, query_vec, top_k=5):
    res = client.search(
        QDRANT_COLLECTION, query_vector=query_vec, limit=top_k, with_payload=True
    )
    return res


def deterministic_query_vec(text: str):
    from convai_narrative_memory_poc.workers.common.utils import get_embedding

    return get_embedding(text)


def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def dedupe_hits_by_text(hits):
    seen_texts = set()
    unique = []
    for h in hits:
        payload = getattr(h, "payload", {}) or {}
        text = payload.get("text")
        key = text.strip().lower() if isinstance(text, str) else None
        if key and key in seen_texts:
            continue
        if key:
            seen_texts.add(key)
        unique.append(h)
    return unique


def select_diverse_scored(scored, desired, embedding_cache):
    if desired <= 0:
        return []

    selected = []
    taken_ids = set()

    for act, h in scored:
        payload = getattr(h, "payload", {}) or {}
        text = payload.get("text")
        if text and text not in embedding_cache:
            embedding_cache[text] = get_embedding(text)

        is_diverse = True
        if text and text in embedding_cache:
            cand_vec = embedding_cache[text]
            for _, existing in selected:
                ex_payload = getattr(existing, "payload", {}) or {}
                ex_text = ex_payload.get("text")
                if not ex_text or ex_text not in embedding_cache:
                    continue
                sim = cosine_similarity(cand_vec, embedding_cache[ex_text])
                if sim >= DIVERSITY_THRESHOLD:
                    is_diverse = False
                    break

        if is_diverse:
            selected.append((act, h))
            taken_ids.add(h.id)
        if len(selected) >= desired:
            break

    if len(selected) < desired:
        for act, h in scored:
            if h.id in taken_ids:
                continue
            selected.append((act, h))
            taken_ids.add(h.id)
            if len(selected) >= desired:
                break

    return selected


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
            hits = dedupe_hits_by_text(hits)
            # Simple activation = similarity * decay * salience
            scored = []
            embedding_cache = {}
            for h in hits:
                pl = h.payload
                decay = decay_weight(pl["stored_at"], now)
                sal = float(pl.get("salience", 1.0))
                act = float(h.score) * decay * sal
                scored.append((act, h))

            scored.sort(key=lambda x: x[0], reverse=True)
            beats = []
            desired = min(MAX_BEATS, top_k, len(scored))
            selected = select_diverse_scored(scored, desired, embedding_cache)
            for act, h in selected:
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
