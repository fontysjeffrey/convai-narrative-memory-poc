# Semantic Memory PoC (Kafka + Qdrant + Reteller)

Tiny-but-real PoC of a **Kafka-driven semantic memory** for a virtual human.
Memories are **anchors** stored as semantic seeds (text + embedding + time + salience).
On recall, we fetch related anchors, let **resonance/decay** shape activation, and ask the LLM to **re-narrate** concisely, with natural fading as time grows.

## Components

- **Kafka topics**: `anchors.write`, `anchors.indexed`, `recall.request`, `recall.response`.
- **Indexer**: consumes anchors, embeds, upserts into Qdrant, emits `anchors.indexed`.
- **Resonance/Recall**: given a cue, pulls nearest anchors, applies time decay + simple spreading activation, returns 2–4 **beats** (anchor text + perceived ages).
- **Reteller**: calls an LLM (or a built‑in stub) to retell concisely, based only on beats + ages (no hard knobs).

## Fast start (dev simulation, no Kafka)

You can run the end-to-end demo without Docker/Kafka to see the fade effect on one machine:

```bash
pip install -r requirements.txt
python scripts/demo_simulation.py
```

This uses an in‑process memory store and a built-in LLM stub (or OpenAI if `OPENAI_API_KEY` is set).

## Full stack (Docker)

Requires Docker. This runs Kafka + Qdrant; workers connect via env vars.

```bash
docker compose up -d
# in another shell: build workers
docker compose build
docker compose up -d indexer resonance reteller
# inject anchors and ask recall
docker compose run --rm tools python tools/seed_and_query.py
# read responses
docker compose logs -f reteller
```

## Env

- `QDRANT_URL` (default `http://qdrant:6333` in docker, `http://localhost:6333` locally)
- `QDRANT_COLLECTION` (default `anchors`)
- `KAFKA_BOOTSTRAP` (default `kafka:9092` in docker; `localhost:9092` locally)
- `OPENAI_API_KEY` (optional for real LLM)
- `OLLAMA_BASE_URL` (optional, e.g. `http://host.docker.internal:11434`)

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)**: System architecture, components, and design decisions
- **[RESEARCH_PROPOSAL.md](RESEARCH_PROPOSAL.md)**: 12-week research plan with validated PoC results
- **[EXPERIMENTAL_METHODOLOGY.md](EXPERIMENTAL_METHODOLOGY.md)**: Complete experimental setup, procedures, and reproducibility
- **[FORGETTING_CURVE.md](FORGETTING_CURVE.md)**: Ebbinghaus forgetting curve theory and implementation
- **[ENV_CONFIG.md](ENV_CONFIG.md)**: Environment configuration for embedding and LLM models

## Notes

- **Embedding**: Now uses BGE-M3 (1024-dim multilingual) via Ollama; falls back to deterministic hashing if unavailable.
- **LLM**: Supports Phi4, Qwen3, Llama3 (via Ollama) or GPT-4o-mini (via OpenAI).
- **Validation**: All experiments are reproducible via `tools/validation_experiments.py` (see EXPERIMENTAL_METHODOLOGY.md).
- This repo favors _clarity over performance_.
