import os, hashlib, numpy as np, datetime as dt, re
from typing import List, Dict, Any

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "anchors")
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")

# Embedding configuration
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "deterministic"
)  # Options: deterministic, nomic-embed-text, mxbai-embed-large, bge-m3
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Embedding dimensions by model
EMBEDDING_DIMS = {
    "deterministic": 384,
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "bge-m3": 1024,
}


def get_embedding_dim() -> int:
    """Get the dimension for the current embedding model."""
    return EMBEDDING_DIMS.get(EMBEDDING_MODEL, 384)


def deterministic_embed(text: str, dim: int = 384) -> List[float]:
    # Fast, deterministic pseudo-embedding based on hashing tokens.
    # Useful for POC/testing without external dependencies
    vec = np.zeros(dim, dtype=np.float32)
    for tok in text.lower().split():
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        idx = h % dim
        vec[idx] += (h % 1000) / 1000.0
    # L2 normalize
    norm = np.linalg.norm(vec) + 1e-9
    return (vec / norm).tolist()


def ollama_embed(text: str, model: str = "nomic-embed-text") -> List[float]:
    """
    Generate embeddings using Ollama.
    Supported models: nomic-embed-text, mxbai-embed-large, bge-m3
    """
    try:
        import requests

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": model, "prompt": text},
            timeout=30,  # Larger models like BGE-M3 need more time
        )
        response.raise_for_status()
        return response.json()["embedding"]
    except Exception as e:
        print(
            f"[embedding] Ollama embedding failed: {e}, falling back to deterministic"
        )
        return deterministic_embed(text)


def get_embedding(text: str) -> List[float]:
    """
    Main embedding function that respects EMBEDDING_MODEL env var.
    """
    if EMBEDDING_MODEL == "deterministic":
        return deterministic_embed(text)
    else:
        # Use Ollama for any other model (nomic-embed-text, mxbai-embed-large, bge-m3)
        return ollama_embed(text, model=EMBEDDING_MODEL)


def human_age(delta: dt.timedelta) -> str:
    days = delta.days
    if days < 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 30:
        return f"{days//7} weeks ago"
    return f"{days // 30} months ago" if days < 365 else f"{days // 365} years ago"


def perceived_age_to_days(perceived_age: str | None) -> float:
    """Rudimentary parser that maps perceived age phrases to an approximate day count."""

    if not perceived_age:
        return float("inf")

    text = perceived_age.strip().lower()
    if not text:
        return float("inf")

    if any(term in text for term in ("just now", "this moment")):
        return 0.0
    if "today" in text:
        return 0.25
    if "yesterday" in text:
        return 1.0

    units = {
        "minute": 1 / 1440,
        "minutes": 1 / 1440,
        "hour": 1 / 24,
        "hours": 1 / 24,
        "day": 1.0,
        "days": 1.0,
        "week": 7.0,
        "weeks": 7.0,
        "month": 30.0,
        "months": 30.0,
        "year": 365.0,
        "years": 365.0,
    }

    number_match = re.search(r"(\d+(?:\.\d+)?)", text)
    value = float(number_match.group(1)) if number_match else 1.0

    for unit, multiplier in units.items():
        if unit in text:
            return value * multiplier

    if any(term in text for term in ("last week", "a week")):
        return 7.0
    if any(term in text for term in ("last month", "a month")):
        return 30.0
    if "last year" in text or "a year" in text:
        return 365.0

    # Fallback for phrases like "last autumn" or unrecognised metaphors
    if any(term in text for term in ("autumn", "fall")):
        return 270.0
    if "spring" in text:
        return 150.0
    if "summer" in text:
        return 90.0
    if "winter" in text:
        return 330.0

    return float("inf")
