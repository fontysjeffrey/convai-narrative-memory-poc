import os, json, uuid, datetime as dt, time
from confluent_kafka import Producer, Consumer

BOOT = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")


def produce_anchor(producer, text, stored_at, meta=None, salience=1.0):
    anchor = {
        "anchor_id": str(uuid.uuid4()),
        "text": text,
        "stored_at": stored_at,
        "meta": meta or {},
        "salience": salience,
    }
    producer.produce("anchors-write", json.dumps(anchor).encode("utf-8"))
    producer.flush()
    return anchor


def request_recall(producer, query, now_iso, top_k=5):
    req = {
        "request_id": str(uuid.uuid4()),
        "query": query,
        "now": now_iso,
        "top_k": top_k,
    }
    producer.produce("recall-request", json.dumps(req).encode("utf-8"))
    producer.flush()
    return req


def main():
    prod = Producer({"bootstrap.servers": BOOT})
    # two anchors at different times
    now = dt.datetime.now(dt.timezone.utc)
    a1_time = (now - dt.timedelta(days=1)).isoformat()
    a2_time = (now - dt.timedelta(days=280)).isoformat()
    a1 = produce_anchor(
        prod,
        "We demoed our Virtual Human to a dozen Fontys colleagues in R10; lively Q&A about memory and ethics.",
        a1_time,
        {"tags": ["vh", "demo"]},
        salience=1.0,
    )
    a2 = produce_anchor(
        prod,
        "At Het Nieuwe Instituut, we ran a small Reflective City pilot; stakeholders debated trust and forgetting.",
        a2_time,
        {"tags": ["rc", "pilot"]},
        salience=0.9,
    )
    print("[tools] seeded anchors", a1["anchor_id"], a2["anchor_id"])

    # ask a recall
    req = request_recall(
        prod,
        "Tell me what happened around our Virtual Human demo.",
        now.isoformat(),
        top_k=5,
    )
    print("[tools] recall request", req["request_id"])
    print("Now tail reteller logs to see response.")


if __name__ == "__main__":
    main()
