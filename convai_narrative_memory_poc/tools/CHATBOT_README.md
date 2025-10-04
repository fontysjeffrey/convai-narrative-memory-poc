# Memory-Enhanced Chatbot Demo

An interactive demonstration of the Kafka-based narrative memory system, designed to showcase time-based memory decay and semantic retrieval for research presentations.

## Quick Start

```bash
# Start the full stack
docker compose -f convai_narrative_memory_poc/docker-compose.yml up -d kafka qdrant indexer resonance reteller

# Run the chatbot
docker compose -f convai_narrative_memory_poc/docker-compose.yml run --rm chatbot
```

## What This Demonstrates

### Semantic Memory Retrieval

Every conversation turn is stored as a semantic "anchor" in Qdrant. When you ask questions, the system:

- Searches for semantically similar memories (not keyword matching)
- Applies time-based decay (Ebbinghaus forgetting curve)
- Returns the most activated memories with their perceived ages

### Time-Based Forgetting

The system implements exponential memory decay:

```
activation = similarity × e^(-λ × age_days) × salience
```

Where:

- `similarity`: Semantic similarity score from vector search
- `λ (lambda)`: Decay constant (default 0.002, ~2 week half-life)
- `age_days`: Days since the memory was stored
- `salience`: Importance weight (0.0 to 1.0)

### Transparent Operations

The chatbot shows you exactly what's happening:

- `*` Memory stored as anchor
- `...` Querying memory system
- `→` Memories recalled with activation scores
- `1.` Individual memory beats with ages
- `>>` Time advanced (for demonstrating decay)

## Example Usage

```
You: I'm researching narrative memory at Fontys with Coen
* Stored anchor: abc12345... | salience: 0.9

You: We're building a virtual human with emotional memory
* Stored anchor: def67890... | salience: 0.9

You: /advance_time 90d
>> Time advanced by 90 days (3 months)

You: What was I researching?
... Querying memory (req: 12ab34cd)
✓ Response received
→ Recalled 2 memories | avg activation: 0.48
 1. "narrative memory at Fontys with Coen" (3 months ago) | activation: 0.52
 2. "virtual human with emotional memory" (3 months ago) | activation: 0.44

Bot: About 3 months ago, you were researching narrative memory at Fontys,
     working with Coen on building a virtual human with emotional memory...
```

## Commands

### Time Manipulation

- `/advance_time 30d` - Advance by 30 days
- `/advance_time 6m` - Advance by 6 months
- `/advance_time 1y` - Advance by 1 year
- `/reset_time` - Reset to present

### Utility

- `/help` - Show all commands
- `/clear` - Clear screen
- `/exit` or `/quit` - Exit chatbot

## Architecture

```
User Input
    ↓
Store as anchor → Kafka (anchors.write)
    ↓
Indexer → Qdrant (vector storage)
    ↓
Query → Kafka (recall.request)
    ↓
Resonance Worker → Qdrant search + decay calculation
    ↓
Kafka (recall.response) → Memory beats
    ↓
Reteller Worker → LLM narrative generation
    ↓
Kafka (retell.response) → Final response
    ↓
Display to user
```

## Research Insights

### What This System Shows

1. **Pure Semantic Memory**: No conversation history in the prompt. Every response is generated solely from semantically retrieved memories.

2. **Realistic Forgetting**: Activation scores decay exponentially. A memory with activation 0.90 (fresh) will drop to approximately 0.45 after 3 months (with default decay rate).

3. **Salience Effects**: Important memories (high salience) resist decay better than casual mentions.

4. **Temporal Awareness**: The system knows when memories were formed and reports ages naturally ("yesterday", "3 months ago", "about a year ago").

5. **Streaming Architecture**: All operations flow through Kafka, making the system auditable, scalable, and resilient.

### Experimental Parameters

Currently configured values (can be adjusted in source):

| Parameter       | Value | Location            | Effect                             |
| --------------- | ----- | ------------------- | ---------------------------------- |
| `λ (lambda)`    | 0.002 | `resonance/main.py` | Decay rate (~2 week half-life)     |
| `MAX_BEATS`     | 3     | `resonance/main.py` | Memories returned per query        |
| `User salience` | 0.9   | `chatbot.py`        | Importance of user statements      |
| `Bot salience`  | 0.7   | `chatbot.py`        | Importance of bot responses        |
| `top_k`         | 5     | `chatbot.py`        | Candidates considered before decay |

### Half-Life Calculation

With λ = 0.002:

- **Half-life**: ln(2) / 0.002 ≈ 347 days (~11.5 months)
- **After 1 week**: ~99% activation remaining
- **After 1 month**: ~94% activation remaining
- **After 3 months**: ~55% activation remaining
- **After 1 year**: ~49% activation remaining

## Troubleshooting

### No memories recalled

```bash
# Check if workers are running
docker compose ps

# Check indexer logs
docker compose logs indexer --tail=20

# Check resonance logs
docker compose logs resonance --tail=20
```

### Slow responses

- Normal: First query takes ~2-3 seconds (Kafka + Qdrant + LLM)
- Each anchor storage includes 1s wait for indexing
- Recall timeout is 15 seconds

### Reset everything

```bash
# Stop all services and remove data
docker compose down -v

# Rebuild and restart
docker compose up -d --build kafka qdrant indexer resonance reteller
sleep 15  # Wait for Kafka initialization

# Create topics
./tools/create_topics.sh

# Restart workers
docker compose restart indexer resonance reteller
```

## For Publications

When citing or describing this system, key points:

- **Not traditional RAG**: This implements episodic memory with temporal dynamics, not document retrieval
- **Psychologically grounded**: Based on Ebbinghaus forgetting curve and spreading activation theory
- **Fully transparent**: Every operation logged and traceable through Kafka
- **Reproducible**: All parameters configurable via environment variables
- **Scalable**: Event-driven architecture allows independent component scaling

## Next Steps for Research

1. **Parameter Tuning**: Experiment with different λ values, salience strategies
2. **Memory Consolidation**: Merge related memories, create episodic structures
3. **Reconsolidation**: Strengthen recently accessed memories
4. **Emotional Weighting**: Add valence/arousal to salience calculations
5. **Cross-lingual**: Test with BGE-M3 embeddings for multilingual memory

## Contact

For questions about this demo or the underlying research:

- Repository: [convai-narrative-memory-poc](https://github.com/...)
- Research Team: Fontys ICT - MindLabs

---

Built with: Python, Kafka, Qdrant, Docker
License: See LICENSE file in repository root
