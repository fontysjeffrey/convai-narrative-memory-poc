import os, json, sys, re, datetime as dt
from confluent_kafka import Consumer, Producer
import random
import requests

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOP_IN = "recall.response"
TOP_OUT = "retell.response"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA = os.getenv("OLLAMA_BASE_URL")

def retell_stub(beats):
    # Natural-feel decay: shorter and fuzzier as ages grow
    ages = [b["perceived_age"] for b in beats]
    # Decide a "freshness" heuristic
    age_weight = 0
    for a in ages:
        if "yesterday" in a or "days" in a or "week" in a: age_weight += 2
        elif "months" in a: age_weight += 1
        else: age_weight += 0
    # Base length
    base = 160 + 20*len(beats)
    length = max(80, base - 30*(len(beats)*2 - age_weight))
    # Compose
    lines = []
    for i,b in enumerate(beats,1):
        t = b["text"]
        # reduce specifics when older
        s = b["perceived_age"]
        if "months" in s or "years" in s:
            t = re.sub(r"\b\d{1,2}[:h][0-5]\d\b","around then",t)
            t = re.sub(r"\b\d{1,2}\b","a handful",t)
            t = re.sub(r"(R\d+|room\s*\w+)", "a room", t, flags=re.I)
        lines.append(f"- {t} ({s})")
    intro = "What I recall, briefly:" if length < 140 else "Here’s how I remember it:"
    out = intro + "\n" + "\n".join(lines)
    return out[:int(length)]

def call_ollama(prompt):
    try:
        r = requests.post(f"{OLLAMA}/api/generate", json={"model":"llama3", "prompt": prompt, "stream": False}, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data.get("response","")
    except Exception as e:
        return None

def call_openai(prompt):
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role":"system","content":"You are a concise, honest narrator whose memory fades with time."},
                      {"role":"user","content": prompt}],
            temperature=0.6
        )
        return resp.choices[0].message.content
    except Exception as e:
        return None

def main():
    consumer = Consumer({'bootstrap.servers': KAFKA_BOOTSTRAP,
                         'group.id':'reteller','auto.offset.reset':'earliest'})
    producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP})
    consumer.subscribe([TOP_IN])
    print("[reteller] listening...")
    while True:
        msg = consumer.poll(1.0)
        if msg is None: 
            continue
        if msg.error():
            print(f"[reteller] error: {msg.error()}", file=sys.stderr); continue
        try:
            payload = json.loads(msg.value().decode('utf-8'))
            request_id = payload["request_id"]
            beats = payload["beats"]
            # Build prompt from beats (no knobs, just perceived ages)
            lines = ["I’m recalling these moments; each ends with how long ago it feels:"]
            lines.extend(f"- {b['text']} ({b['perceived_age']})" for b in beats)
            lines.append("Please retell it concisely like a human memory—fewer crisp details when older, keep gist intact.")
            prompt = "\n".join(lines)
            text = None
            if OPENAI_API_KEY:
                text = call_openai(prompt)
            if text is None and OLLAMA:
                text = call_ollama(prompt)
            if text is None:
                text = retell_stub(beats)
            out = {"request_id": request_id, "retelling": text}
            producer.produce(TOP_OUT, json.dumps(out).encode('utf-8'))
            producer.flush()
            print(f"[reteller] retold {request_id}")
        except Exception as e:
            print(f"[reteller] exception: {e}", file=sys.stderr)
    consumer.close()

if __name__ == "__main__":
    main()
