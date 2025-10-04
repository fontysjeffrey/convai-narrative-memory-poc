# Concept Dictionary

This reference captures the key ideas, components, and terminology used across the Conversational AI Narrative Memory proof-of-concept. Each entry links back to the anchor-and-flux paradigm where durable event memories and adaptive retellings combine to create human-like identity.

---

## Terms

### Anchor

Durable factual memory fragment (who/what/where/when) stored with metadata and a semantic embedding. Anchors are immutable once written so the system retains a coherent autobiographical backbone.

### Anchor-and-Flux Model

Core paradigm asserting that virtual human identity emerges from the interplay of unchanging anchors and adaptive flux narratives, replacing rigid personality sliders with evolving stories.

### Beats

Ranked recall results emitted by the resonance worker. Each beat bundles an anchor’s text, perceived age, and activation score so the reteller can stitch them into a response.

### BGE-M3 Embeddings

1024-dimensional multilingual sentence embeddings served via Ollama. They underpin cross-lingual memory retrieval and are the production default for the indexer.

### Flux

Adaptive retelling of anchors. Flux responses vary detail, tone, and certainty based on context, perceived age, and character settings, ensuring recollections feel human instead of robotic.

### Flux Detail Degradation

Rule set applied by the reteller that intentionally blurs specifics (numbers, times, locations) for older memories so narratives degrade gracefully with age.

### Kafka Topics

Event streams (`anchors.write`, `anchors.indexed`, `recall.request`, `recall.response`, `retell.response`) that decouple microservices and log every memory lifecycle transition.

### Multi-Factor Activation

Recall scoring function combining semantic similarity, temporal decay, and salience. The highest activations determine which anchors surface as beats.

### Ollama

Local model runtime supplying both embedding (BGE-M3) and retelling LLMs (Phi4, Qwen3, Llama3). Enables fast, private experimentation without external APIs.

### Perceived Age

Human-readable time label (e.g., “yesterday”, “months ago”) derived from an anchor’s decay weight. Guides the reteller’s level of specificity and confidence.

### Qdrant

Vector database storing anchor embeddings and payloads. Provides cosine similarity search with metadata filters to fuel resonance queries.

### Resonance Worker

Recall microservice that embeds queries, searches Qdrant, applies multi-factor activation, attaches perceived ages, and emits beats to Kafka.

### Reteller Worker

Narrative generator that consumes beats and produces age-aware responses via configurable LLMs or a deterministic stub. Ensures memory outputs match desired character tone.

### Salience

Anchor importance weight (typically 0.3–2.5) reflecting emotional or operational significance. High-salience anchors counteract decay, mimicking flashbulb memories.

### Shared vs. Private Memory (Planned)

Upcoming multi-agent extension distinguishing individual anchors from team knowledge. Includes provenance tracking so agents can say “I remember” versus “I heard from X.”

### Temporal Decay (λ = 0.002)

Ebbinghaus-inspired exponential forgetting curve applied per day. Balances recency bias with long-term continuity and underpins perceived age calculations.

### Validation Experiments

Automated suite (`tools/validation_experiments.py`) that seeds a synthetic corpus, sweeps decay rates, and confirms λ = 0.002 best matches human-like recall patterns.

### Memory Security (Planned)

Research roadmap covering authentication, encryption, audit trails, and GDPR-aligned deletion to guard against memory injection and unauthorized access.

---

_Last updated: October 3, 2025_
