import os, hashlib, numpy as np, datetime as dt
from typing import List, Dict, Any

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "anchors")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

def deterministic_embed(text: str, dim: int = 384) -> List[float]:
    # Fast, deterministic pseudo-embedding based on hashing tokens.
    vec = np.zeros(dim, dtype=np.float32)
    for tok in text.lower().split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += ((h % 1000) / 1000.0)
    # L2 normalize
    norm = np.linalg.norm(vec) + 1e-9
    return (vec / norm).tolist()

def human_age(delta: dt.timedelta) -> str:
    days = delta.days
    if days < 1: return "yesterday"
    if days < 7: return f"{days} days ago"
    if days < 30: return f"{days//7} weeks ago"
    if days < 365: return f"{days//30} months ago"
    return f"{days//365} years ago"
