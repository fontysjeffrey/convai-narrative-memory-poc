import datetime as dt, uuid, numpy as np
from workers.common.utils import deterministic_embed, human_age

# In-memory store (like a tiny Qdrant)
store = []

def add_anchor(text, days_ago, salience=1.0):
    now = dt.datetime.utcnow()
    stored_at = now - dt.timedelta(days=days_ago)
    store.append({
        "id": str(uuid.uuid4()),
        "text": text,
        "vec": deterministic_embed(text),
        "stored_at": stored_at,
        "salience": salience
    })

def cosine(a,b):
    return float(np.dot(a,b) / (np.linalg.norm(a)*np.linalg.norm(b) + 1e-9))

def search(query, k=5):
    q = deterministic_embed(query)
    scored = []
    for m in store:
        scored.append((cosine(q, m["vec"]), m))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _,m in scored[:k]]

def decay_weight(stored_at, now, lam=0.002):
    age_days = (now - stored_at).days
    return np.exp(-lam * max(age_days,0))

def resonate(query, k=5, beats=3):
    now = dt.datetime.utcnow()
    hits = search(query, k=k)
    scored = []
    for m in hits:
        act = decay_weight(m["stored_at"], now) * 1.0  # * salience
        scored.append((act, m))
    scored.sort(key=lambda x: x[0], reverse=True)
    pick = [m for _,m in scored[:beats]]
    return [{"text": m["text"], "age": human_age(now - m["stored_at"])} for m in pick]

def retell_from_beats(beats):
    # human-like: crisp if fresh, gist if old
    parts = [f"- {b['text']} ({b['age']})" for b in beats]
    if any("years" in b["age"] or "months" in b["age"] for b in beats):
        intro = "What sticks with me:"
    elif any("week" in b["age"] or "days" in b["age"] for b in beats):
        intro = "From what I remember:"
    else:
        intro = "Yesterday was clear:"
    return intro + "\n" + "\n".join(parts)

def main():
    add_anchor("We demoed our Virtual Human to a dozen Fontys colleagues in R10; lively Q&A about memory and ethics.", 1)
    add_anchor("At Het Nieuwe Instituut, we ran a small Reflective City pilot; stakeholders debated trust and forgetting.", 280)

    beats = resonate("Tell me what happened around our Virtual Human demo.", k=5, beats=2)
    print("BEATS ->", beats)
    print("\nRETELLING\n", retell_from_beats(beats))

if __name__ == "__main__":
    main()
