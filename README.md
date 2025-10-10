# ConvAI Narrative Memory PoC

Tiny-but-real proof of concept of a Kafka + Qdrant memory loop for a virtual human. We store every utterance as an "anchor", recall the most relevant ones with time decay, and ask an LLM to weave them into a short recap.

---

## Quick Start (Docker)

1. **Reset storage & topics** – ensures Qdrant matches the current embedding size and Kafka topics exist.
   ```bash
   bash convai_narrative_memory_poc/tools/create_topics.sh
   ```
2. **Boot the workers**
   ```bash
   docker compose -f convai_narrative_memory_poc/docker-compose.yml up -d \
     kafka qdrant indexer resonance reteller
   ```
3. **Open the interactive chatbot**
   ```bash
   docker compose -f convai_narrative_memory_poc/docker-compose.yml run --rm chatbot
   ```
   - `/reset_session` → start a clean session (current chat is ignored for recall)
   - `/advance_time 90d` → simulate forgetting curves
   - `/reset_time` → jump back to present

The reteller now ignores anchors from the live session and anything younger than ~5 seconds, so the recap only cites prior memories.

When you are done:

```bash
docker compose -f convai_narrative_memory_poc/docker-compose.yml down
```

---

## Other Demos

| Demo                | Command                                                                                                      | What it shows                                                           |
| ------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------- |
| Three retells       | `docker compose -f ... run --rm tools python convai_narrative_memory_poc/tools/demo_three_retells.py`        | Seeds three anchors (recent → months) and prints beats + narrated recap |
| Seed & query script | `docker compose -f ... run --rm tools python convai_narrative_memory_poc/tools/seed_and_query.py`            | Simple end-to-end seed and recall without the chatbot                   |
| Inspect Qdrant      | `docker compose -f ... run --rm tools python convai_narrative_memory_poc/tools/inspect_qdrant.py --limit 20` | Peek at stored anchors                                                  |

---

## Model Selection Cheatsheet

Set these env vars before starting the stack (Docker Compose already reads them):

| Purpose                   | Env var                   | Example                             | Notes                                                                                                      |
| ------------------------- | ------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Chat LLM                  | `PORTKEY_MODEL`           | `mistral-large`                     | Routed through Fontys Portkey gateway. Prefix with `portkey:` if you prefer (`portkey:mistral-large`).     |
| Embeddings                | `EMBEDDING_MODEL`         | `ollama:bge-m3`                     | Prefix `portkey:` for remote models or `ollama:` for local Ollama embeddings. Defaults to `ollama:bge-m3`. |
| Remote embedding override | `PORTKEY_EMBEDDING_MODEL` | `portkey:cohere-embed-v3`           | Optional; use when Fontys enables the model. Falls back to deterministic vectors if the call fails.        |
| Local Ollama endpoint     | `OLLAMA_BASE_URL`         | `http://host.docker.internal:11434` | Needed if you keep Ollama outside Docker.                                                                  |

If no remote embedding is available, the system stays on Ollama **bge-m3** and falls back to deterministic hashing for safety.

---

## Local (no Docker)

```bash
pip install -r requirements.txt
python scripts/demo_simulation.py
```

This uses the same logic with an in-process store; handy for quick visualization without Kafka.

---

## Handy Commands

```bash
bash convai_narrative_memory_poc/tools/create_topics.sh   # reset Qdrant + create Kafka topics (anchors-write, recall-request, ...)

docker compose -f convai_narrative_memory_poc/docker-compose.yml logs -f reteller   # watch reteller output

docker compose -f convai_narrative_memory_poc/docker-compose.yml run --rm tools python convai_narrative_memory_poc/tools/validation_experiments.py
```

---

## Docs & Reading

- `research/anchor_flux_model.md` – conceptual overview (start here)
- `research/architecture.md` – system diagram and design notes
- `research/env_config.md` – more detail on model choices and environment variables
- `convai_narrative_memory_poc/tools/CHATBOT_DEMO.md` – walkthrough of the interactive CLI

---

_This repo favors clarity over raw performance. Pull requests with improved ergonomics are welcome!_
