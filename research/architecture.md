# Conversational AI Narrative Memory System Architecture

## Overview

This system implements a realistic, psychologically-grounded memory system for conversational AI agents (Virtual Humans). Unlike traditional retrieval-augmented generation (RAG) systems that simply return the most similar documents, this architecture models how human memory actually works: memories fade over time, activation strength varies, and recall is influenced by both recency and emotional salience.

## Core Concept

The system transforms text-based experiences into persistent, searchable memory "anchors" that can be retrieved with realistic time-based decay and activation patterns. When the AI recalls memories, it doesn't just get raw text—it receives contextual information about how old each memory feels and how strongly it's activated, allowing for more natural, human-like responses.

## System Architecture

The system is built on a **microservices architecture** using **event-driven communication**. This means that instead of components calling each other directly, they communicate by sending and receiving messages through a central message broker (Apache Kafka). This design provides several key benefits:

1. **Decoupling**: Each component operates independently and can be updated or scaled without affecting others
2. **Resilience**: If one component temporarily fails, messages wait in the queue until it recovers
3. **Auditability**: Every memory operation creates a traceable event in the system
4. **Scalability**: Components can be replicated to handle increased load

### Component Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Apache Kafka (Message Broker)               │
│  Topics: anchors-write → anchors-indexed → recall-request →         │
│          recall.response → retell.response                          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↕
        ┌──────────────┬────────────┼────────────┬──────────────┐
        ↓              ↓            ↓            ↓              ↓
   ┌─────────┐   ┌─────────┐  ┌─────────┐  ┌─────────┐   ┌─────────┐
   │ Indexer │   │Resonance│  │Reteller │  │ Qdrant  │   │  Tools  │
   │ Worker  │   │ Worker  │  │ Worker  │  │Vector DB│   │(Client) │
   └─────────┘   └─────────┘  └─────────┘  └─────────┘   └─────────┘
```

## Detailed Component Descriptions

### 1. Apache Kafka (Message Broker)

**What it does**: Kafka acts as the nervous system of our memory architecture. It's a distributed streaming platform that reliably stores and forwards messages between components.

**Why Kafka and not direct API calls?**

- **Temporal decoupling**: The producer and consumer don't need to be running simultaneously
- **Message persistence**: All memory events are stored (configurable retention) for replay or debugging
- **Order guarantees**: Within a partition, messages are processed in the exact order they were produced
- **Backpressure handling**: Fast producers don't overwhelm slow consumers

**Topics in this system**:

- `anchors-write`: Raw memory experiences waiting to be processed
- `anchors.indexed`: Confirmation that memories have been embedded and stored
- `recall.request`: Queries asking the system to remember something
- `recall.response`: Retrieved memory "beats" with activation scores
- `retell.response`: Final narrative reconstruction of the memory

### 2. Indexer Worker

**Input**: Listens to `anchors-write` topic  
**Output**: Writes to `anchors.indexed` topic, stores in Qdrant

**What it does**: This component is responsible for transforming raw text memories into searchable vector representations and storing them permanently.

**Process**:

1. Consumes a memory anchor from the `anchors-write` topic
2. Generates a semantic embedding (vector representation) of the text using the configured embedding model:
   - **Deterministic** (384-dim): Fast, zero dependencies, good for testing
   - **Nomic-embed-text** (768-dim): Excellent English semantic search, 274 MB
   - **MXBai-embed-large** (1024-dim): High-quality retrieval, 669 MB
   - **BGE-M3** (1024-dim): **Multilingual** (100+ languages), state-of-the-art, 1.2 GB
3. Stores the anchor in Qdrant vector database with metadata:
   - Original text
   - Timestamp (`stored_at`)
   - Emotional/importance weight (`salience`)
   - Optional metadata tags
   - Vector dimension automatically matches the embedding model
4. Publishes confirmation to `anchors.indexed` topic

**Key Feature**: The system automatically detects dimension mismatches and recreates the Qdrant collection when switching embedding models, ensuring compatibility.

### 3. Qdrant (Vector Database)

**What it does**: Qdrant is a specialized database optimized for storing and searching high-dimensional vectors. It's the long-term memory storage of the system.

**Key features for this use case**:

- **Similarity search**: Given a query vector, find the most similar stored vectors (nearest neighbor search)
- **Filtered search**: Can combine vector similarity with metadata filters (e.g., "find similar memories from last month")
- **Payload storage**: Stores the original text and metadata alongside the vectors
- **Fast retrieval**: Optimized for sub-second search even with millions of vectors

### 4. Resonance Worker

**Input**: Listens to `recall.request` topic  
**Output**: Writes to `recall.response` topic

**What it does**: This is the psychological heart of the system. It implements time-based memory decay and activation patterns inspired by cognitive psychology.

**Process**:

1. Consumes a recall request containing:
   - Query text ("Tell me about the demo")
   - Current timestamp
   - Number of memories to retrieve (`top_k`)
2. Generates a query embedding for the input text
3. Searches Qdrant for semantically similar anchors
4. Applies **temporal decay**: Calculates how much each memory has faded based on age
   ```
   decay = exp(-λ × age_in_days)
   ```
   where λ (lambda) is the decay constant (default 0.002)
5. Calculates **activation strength**: Combines semantic similarity, time decay, and salience
   ```
   activation = similarity_score × decay × salience
   ```
6. Selects the top N most-activated memories as "beats"
7. For each beat, computes a human-readable age description ("yesterday", "about 9 months ago")
8. Publishes the beats with activation scores to `recall.response`

**Why this matters**: This approach models **forgetting** and **recency bias** naturally. Recent, emotionally significant memories dominate recall, while older memories require stronger semantic matches to resurface.

### 5. Reteller Worker

**Input**: Listens to `recall.response` topic  
**Output**: Writes to `retell.response` topic

**What it does**: Takes the raw memory beats and reconstructs them into a coherent narrative, optionally using an LLM for natural language generation.

**Process**:

1. Consumes recall response containing beats (text snippets + perceived ages + activations)
2. Constructs a prompt from the beats with age context
3. **Three modes of operation** (tried in order: OpenAI → Ollama → Stub):
   - **OpenAI mode**: Uses GPT models (gpt-4o, gpt-4o-mini) for sophisticated narrative generation
   - **Ollama mode**: Uses local LLMs for privacy-preserving narrative reconstruction:
     - **Phi4** (9.1 GB): Fast, direct narratives without reasoning overhead (recommended)
     - **Qwen3** (5.2 GB): Excellent reasoning, includes `<think>` tags (auto-filtered)
     - **Llama3** (4.7 GB): Good all-rounder, balanced performance
     - **Gemma3** (8-12 GB): High-quality output
   - **Stub mode** (fallback): Simple concatenation with age annotations and detail reduction for older memories
4. Publishes the final narrative to `retell.response`

**Design philosophy**: The reteller is intentionally modular. The system works without LLM involvement (stub mode), but can be enhanced with increasingly sophisticated language models. This allows for:

- **Fast prototyping** without API costs (stub mode)
- **Privacy-preserving** local inference (Ollama)
- **Production deployment** with powerful cloud models (OpenAI)
- **Configurable models** via environment variables (no code changes needed)

**Special handling**: Qwen3's chain-of-thought reasoning (enclosed in `<think>` tags) is automatically filtered out to return only the final narrative.

### 6. Tools (Client Application)

**What it does**: Demonstrates the system by acting as both memory creator and memory consumer. In production, this would be your application layer.

**Capabilities**:

- Seeds example memories (anchors) into the system
- Requests memory recall
- (Could be extended to) Listen for retelling responses

## Data Flow: Complete Memory Lifecycle

Let's trace a memory from creation to recall:

### Phase 1: Memory Formation (Indexing)

```
1. Application creates anchor:
   {
     "anchor_id": "550e8400-e29b-41d4-a716-446655440000",
     "text": "We demoed our Virtual Human at Fontys; lively Q&A about ethics",
     "stored_at": "2025-10-01T14:30:00Z",
     "salience": 1.0,
     "meta": {"tags": ["demo", "fontys"]}
   }

2. Application → Kafka (anchors-write)

3. Indexer consumes message
   - Generates embedding: [0.23, -0.45, 0.12, ..., 0.67] (768 dimensions)
   - Stores in Qdrant with full payload
   - Confirms to Kafka (anchors.indexed)

4. Memory is now searchable
```

### Phase 2: Memory Recall

```
1. Application creates recall request:
   {
     "request_id": "123e4567-e89b-12d3-a456-426614174000",
     "query": "What happened at the demo?",
     "now": "2025-10-02T10:00:00Z",
     "top_k": 5
   }

2. Application → Kafka (recall.request)

3. Resonance consumes message
   - Embeds query: [0.21, -0.43, 0.15, ..., 0.69]
   - Searches Qdrant → finds semantic matches
   - Anchor stored ~20 hours ago
   - Calculates: decay = exp(-0.002 × 0.83) = 0.998
   - Calculates: activation = 0.89 × 0.998 × 1.0 = 0.888
   - Returns top 3 beats

4. Resonance → Kafka (recall.response):
   {
     "request_id": "123e4567-e89b-12d3-a456-426614174000",
     "beats": [
       {
         "anchor_id": "550e8400-...",
         "text": "We demoed our Virtual Human at Fontys...",
         "perceived_age": "yesterday",
         "activation": 0.888
       },
       {...},
       {...}
     ]
   }

5. Reteller consumes recall.response
   - In stub mode: concatenates beats with age context
   - In LLM mode: prompts model to weave beats into narrative
   - Returns: "Yesterday, we demonstrated our Virtual Human at Fontys.
              The session included a lively Q&A focused on ethical considerations..."

6. Reteller → Kafka (retell.response)

7. Application consumes and presents to user
```

## Key Design Decisions and Trade-offs

### 1. Event-Driven vs. Request-Response Architecture

**Chosen**: Event-driven (Kafka)  
**Alternative**: RESTful APIs between services

**Rationale**:

- Memory operations are naturally asynchronous—storage and recall don't need instant responses
- Event logs provide complete audit trails for debugging memory behavior
- System can be replayed from any point for testing
- Natural fit for streaming applications where memories accumulate continuously

**Trade-off**: Added complexity of managing Kafka infrastructure and eventual consistency

### 2. Separate Indexer and Resonance Workers

**Chosen**: Two specialized services  
**Alternative**: Single "memory service" handling both

**Rationale**:

- Indexing (write-heavy, CPU-intensive embedding) has different scaling needs than recall (read-heavy, I/O bound)
- Separation of concerns: indexer focuses on storage correctness, resonance focuses on psychological realism
- Can update activation algorithms without touching storage logic

**Trade-off**: More moving parts to deploy and monitor

### 3. Embedding Model Strategy

**Implemented**: Configurable via `EMBEDDING_MODEL` environment variable  
**Options**: `deterministic` (default), `nomic-embed-text`, `mxbai-embed-large`, `bge-m3`

**Design decision**: Rather than choosing a single embedding approach, the system supports multiple models with automatic dimension handling:

| Model                 | Dimensions | Size   | Best For                               |
| --------------------- | ---------- | ------ | -------------------------------------- |
| **deterministic**     | 384        | 0 MB   | Fast testing, no dependencies          |
| **nomic-embed-text**  | 768        | 274 MB | English semantic search, speed         |
| **mxbai-embed-large** | 1024       | 669 MB | High-quality retrieval                 |
| **bge-m3**            | 1024       | 1.2 GB | **Multilingual**, cross-lingual search |

**Production consideration**: For Dutch/English mixed environments (like Fontys), **BGE-M3** is recommended as it excels at multilingual and cross-lingual retrieval. For English-only applications, `nomic-embed-text` offers the best speed/quality balance.

**Technical implementation**: The indexer automatically detects vector dimension mismatches and recreates the Qdrant collection when switching models, preventing compatibility errors.

### 4. Temporal Decay Function

**Chosen**: Exponential decay with configurable λ  
**Alternative**: Power-law decay, spaced repetition schedules

**Rationale**:

- Exponential decay is psychologically validated (Ebbinghaus forgetting curve)
- Single parameter (λ) is easy to tune
- Computationally cheap: `exp(-λ × days)`

**Extensibility**: System could support multiple decay functions or per-anchor decay rates based on memory type

### 5. Kafka vs. Other Message Brokers

**Kafka chosen over**:

- **RabbitMQ**: Kafka's log-based storage better fits memory audit trails; higher throughput
- **Redis Streams**: Kafka provides stronger durability guarantees; better multi-consumer support
- **AWS SQS**: Kafka is self-hosted (no vendor lock-in); better message ordering guarantees

**Trade-off**: Kafka has a steeper learning curve and more complex deployment

## Scaling Considerations

### Horizontal Scaling

Each component can scale independently:

**Indexer**:

- Add more indexer instances
- Kafka automatically distributes partition load
- Bottleneck: Qdrant write throughput

**Resonance**:

- Add more resonance instances
- Each can process different recall requests in parallel
- Bottleneck: Qdrant read throughput

**Reteller**:

- Add more reteller instances
- LLM API calls can parallelize well
- Bottleneck: LLM API rate limits or inference costs

**Qdrant**:

- Can cluster for high availability
- Sharding for very large memory stores (millions of anchors)

### Partitioning Strategy

Currently: Single partition per topic (simple, ordered)  
Production: Could partition by:

- User ID (memories for different users processed independently)
- Memory type (episodic vs semantic vs procedural)
- Time range (recent vs archival memories)

## Testing and Development

### Local Development (Fast Start)

Use `convai_narrative_memory_poc/tools/validation_experiments.py` to replay anchors, run recall + retell, and inspect activation scores without Kafka:

- Pure Python execution (no Docker required)
- Prints beats, retell output, and helpful diagnostics
- Great for tweaking decay parameters or resonance heuristics

### Full Stack (This Docker Compose Setup)

All services containerized for realistic production-like testing:

- Kafka with KRaft mode (no Zookeeper dependency)
- Persistent Qdrant storage
- Realistic network delays and failure modes

### Testing Strategies

**Unit tests**: Individual components (embedding functions, decay calculations)  
**Integration tests**: Component pairs (indexer + Qdrant)  
**End-to-end tests**: Full memory lifecycle via Kafka  
**Replay tests**: Reprocess historical Kafka logs to test algorithm changes

## Monitoring and Observability

Key metrics to track in production:

**Indexer**:

- Messages/second indexed
- Qdrant insertion latency
- Embedding generation time

**Resonance**:

- Query latency (search + activation calculation)
- Activation score distributions (are memories decaying as expected?)
- Top-k retrieval time

**Reteller**:

- LLM API latency
- Narrative generation time
- Token usage (costs)

**Kafka**:

- Consumer lag (is any component falling behind?)
- Message throughput per topic
- Rebalancing events

## Configuration

The system is fully configurable via environment variables, allowing model selection without code changes:

### Embedding Configuration

```bash
# Choose your embedding model
EMBEDDING_MODEL=bge-m3              # Options: deterministic, nomic-embed-text, mxbai-embed-large, bge-m3
OLLAMA_BASE_URL=http://localhost:11434
```

**Recommendation**: Use `bge-m3` for multilingual applications, `nomic-embed-text` for English-only with best performance.

### Retelling Configuration

```bash
# Ollama LLM for retelling
OLLAMA_MODEL=phi4                   # Options: phi4, qwen3, llama3, gemma3:12b, etc.

# Or use OpenAI (tried first if set)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini           # Options: gpt-4o-mini, gpt-4o, gpt-3.5-turbo
```

**Recommendation**: Use `phi4` for fast, clean narratives. Use `qwen3` if you want deeper reasoning (automatically filtered). Use OpenAI for production quality.

### Infrastructure Configuration

```bash
KAFKA_BOOTSTRAP=localhost:9092
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=anchors
```

**Configuration file**: Place these in a `.env` file in the same directory as `docker-compose.yml`, or export them as environment variables. See `ENV_CONFIG.md` for detailed examples and troubleshooting.

## Future Enhancements

### Near-term

1. ~~**Production embeddings**: Replace deterministic embeddings with sentence-transformers~~ ✅ **DONE** - Now supports BGE-M3, Nomic, and MXBai via Ollama
2. **Memory consolidation**: Merge similar memories that occur close in time
3. **Forgetting mechanisms**: Actively remove or archive very old, low-activation memories
4. **Configuration UI**: Web interface for tuning decay rates, activation thresholds, and model selection

### Medium-term

1. **Episodic structure**: Link related memories into narrative episodes
2. **Emotional tagging**: Detect and weight emotional content in memories
3. **Personalization**: Per-user decay rates and activation thresholds

### Research directions

1. **Reconsolidation**: Memories accessed recently could have their timestamps updated (as in human memory)
2. **False memories**: Probabilistically blend or confuse similar memories
3. **Metacognition**: System reports confidence in recall ("I think this happened...")

## Conclusion

This architecture demonstrates that realistic, psychologically-grounded memory systems for AI don't require monolithic models or complex prompt engineering. By separating concerns—storage, retrieval, activation dynamics, and narrative generation—we create a system that is:

- **Transparent**: Every memory operation is traceable through Kafka event logs
- **Tunable**: Psychological parameters and models can be adjusted via environment variables without code changes
- **Scalable**: Components scale independently based on load (indexer, resonance, reteller can each scale horizontally)
- **Testable**: Each component can be validated in isolation
- **Extensible**: New memory types or recall strategies slot in naturally
- **Multilingual**: BGE-M3 embeddings enable cross-lingual semantic search (query in English, find Dutch memories and vice versa)
- **Production-ready**: From local testing (deterministic embeddings + stub) to production (BGE-M3 + GPT-4) with zero code changes

The event-driven architecture might seem complex initially, but it provides the flexibility and robustness required for production conversational AI systems where memory isn't just retrieval—it's a dynamic, temporally-aware process that mirrors human cognition.

**Current Implementation**: The system is operational with BGE-M3 multilingual embeddings (1024-dim) and Phi4 for natural narrative generation, successfully processing memories through the complete Kafka → Qdrant → Resonance → Retelling pipeline with psychologically realistic time-based decay and activation.
