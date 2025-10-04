# Experimental Methodology: Validation of Ebbinghaus Forgetting Curve Implementation

**Document Version:** 1.0  
**Experiment Date:** October 2, 2025  
**Timestamp:** 2025-10-02T11:27:17+00:00

---

## 1. Overview

This document details the complete experimental methodology for validating the Ebbinghaus forgetting curve implementation in our conversational AI memory system. All experiments were designed to be reproducible and automated via `validation_experiments.py`.

---

## 2. Experimental Infrastructure

### 2.1 Software Stack

| Component  | Version            | Purpose                                                      |
| ---------- | ------------------ | ------------------------------------------------------------ |
| **Python** | 3.12               | Experiment execution environment                             |
| **Ollama** | Latest             | Local LLM and embedding server                               |
| **BGE-M3** | Latest             | Multilingual embedding model (1024 dimensions)               |
| **Qdrant** | 1.9.2              | Vector database for semantic search                          |
| **Kafka**  | Latest (Confluent) | Event streaming (not used in validation, but part of system) |
| **Docker** | Latest             | Containerization and orchestration                           |
| **uv**     | Latest             | Python package management                                    |

### 2.2 Hardware Configuration

- **GPU Workstation**: Required for Ollama (BGE-M3 embeddings)
- **CPU**: Modern multi-core processor (Docker containers)
- **RAM**: Minimum 16GB (Ollama + Docker services)
- **Storage**: SSD recommended for Qdrant performance

### 2.3 Docker Compose Setup

Services running during validation:

```yaml
services:
  qdrant:
    image: qdrant/qdrant:v1.9.2
    ports: ["6333:6333"]

  tools:
    build: ./tools
    depends_on: [qdrant]
    environment:
      - QDRANT_URL=http://qdrant:6333
      - EMBEDDING_MODEL=bge-m3
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**Note:** Kafka was running but not used in validation (no message passing needed for static tests).

---

## 3. Test Corpus Design

### 3.1 Memory Selection Criteria

We designed 8 synthetic memories to cover realistic conversational memory scenarios:

**Temporal Coverage:**

- Recent: 1-2 days (recent events)
- Short-term: 7-14 days (last week/fortnight)
- Medium-term: 30 days (last month)
- Long-term: 120-270 days (months/seasons ago)

**Salience Distribution:**

- Low (0.3): Trivial conversations (weather chat)
- Normal (0.8-1.2): Routine work events (meetings, kickoffs)
- High (1.3-1.5): Significant events (demonstrations, brainstorming)
- Critical (2.5): Major incidents (system outages)

**Content Categories:**

- Professional: Work meetings, demos, standups
- Technical: System issues, conferences
- Social: Hallway conversations
- Creative: Brainstorming sessions

### 3.2 Complete Test Corpus

| ID  | Text                                                                                                                | Days Ago | Salience | Category               | Rationale                                           |
| --- | ------------------------------------------------------------------------------------------------------------------- | -------- | -------- | ---------------------- | --------------------------------------------------- |
| 1   | "Demonstrated Virtual Human to 12 Fontys colleagues in R10 at 14:30. Engaging Q&A about ethics and data retention." | 1        | 1.5      | recent_high_salience   | Recent, detailed, significant event                 |
| 2   | "Coffee meeting with project sponsor to discuss budget allocation for Q2."                                          | 30       | 1.0      | medium_normal_salience | Medium-age, routine professional event              |
| 3   | "Initial project kickoff meeting where we defined the scope of the narrative memory system."                        | 270      | 1.2      | old_high_salience      | Very old but foundational event                     |
| 4   | "Casual hallway conversation about the weather and weekend plans."                                                  | 2        | 0.3      | recent_low_salience    | Recent but trivial (should rank low)                |
| 5   | "Critical system outage affecting 50+ users, required emergency fix and stakeholder communication."                 | 180      | 2.5      | old_critical_salience  | Old but extremely important (flashbulb memory test) |
| 6   | "Weekly standup meeting covering sprint progress and blockers."                                                     | 7        | 0.8      | recent_routine         | Recent routine event                                |
| 7   | "Brainstorming session for new features including multi-agent interactions and character-driven memory."            | 14       | 1.3      | recent_creative        | Recent creative/strategic event                     |
| 8   | "Attended conference talk about vector databases and semantic search in AI systems."                                | 120      | 1.1      | old_educational        | Old educational event                               |

### 3.3 Timestamp Calculation

All memories were backdated from experiment start time:

```python
experiment_time = datetime(2025, 10, 2, 11, 27, 17, tzinfo=timezone.utc)
stored_at = experiment_time - timedelta(days=days_ago)
```

Example:

- Memory ID 1 (1 day ago): `stored_at = 2025-10-01T11:27:17+00:00`
- Memory ID 3 (270 days ago): `stored_at = 2025-01-05T11:27:17+00:00`

---

## 4. Embedding Generation

### 4.1 Model Selection: BGE-M3

**Why BGE-M3?**

- **Multilingual**: Supports 100+ languages (important for future internationalization)
- **High dimensionality**: 1024 dimensions (better semantic capture than 384/768)
- **State-of-the-art**: Top performance on MTEB benchmark
- **Local execution**: No API costs or privacy concerns

### 4.2 Embedding Process

```python
def ollama_embed(text: str, model: str = "bge-m3") -> List[float]:
    """Generate embeddings via Ollama API"""
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=30
    )
    return response.json()["embedding"]  # 1024-dim vector
```

**Parameters:**

- `model`: "bge-m3"
- `timeout`: 30 seconds (larger models need time)
- `base_url`: `http://host.docker.internal:11434` (Docker → host machine Ollama)

### 4.3 Embedding Storage

Embeddings stored in Qdrant with metadata:

```python
PointStruct(
    id=memory_id,
    vector=embedding,  # 1024-dim float array
    payload={
        "text": original_text,
        "stored_at": iso_timestamp,
        "salience": float,
        "category": string,
        "days_ago": int  # For analysis only
    }
)
```

**Collection Configuration:**

- Name: `validation_anchors` (isolated from production `anchors`)
- Vector size: 1024 (matches BGE-M3)
- Distance metric: Cosine similarity
- Recreated before each experiment run (ensures clean slate)

---

## 5. Query Design

### 5.1 Query 1: Temporal Prioritization Test

**Text:** "Tell me about the demonstration and project meetings"

**Design Rationale:**

- Semantic overlap with multiple memories (demo, kickoff, standup, brainstorming)
- Tests whether recent relevant memories outrank older ones
- Moderate similarity scores (no perfect match)

**Expected Behavior:**

- Demo (ID 1, 1 day old) should rank high due to recency + relevance
- Kickoff (ID 3, 270 days old) may rank depending on λ (high salience but very old)
- Standup (ID 6, 7 days old) should rank moderately (routine, lower salience)

### 5.2 Query 2: Salience × Decay Interaction Test

**Text:** "system problems and emergencies"

**Design Rationale:**

- Strong semantic match to system outage (ID 5)
- Weak match to most other memories
- Tests whether high salience overcomes temporal decay

**Expected Behavior:**

- System outage (ID 5, 180 days old, salience 2.5) should rank #1 despite age
- Recent low-salience memories (hallway chat) should rank low despite recency

### 5.3 Query 3: Temporal Progression (Simulated)

**Text:** "demonstration to colleagues"

**Design Rationale:**

- Direct match to demo memory (ID 1)
- Used to simulate aging of a single memory over time
- Fixed similarity score, varying only time distance

**Method:**

- Don't actually age the memory in database
- Calculate activation for different `days_ago` values: 0, 1, 7, 30, 90, 180, 365, 730
- Demonstrates pure temporal decay curve

---

## 6. Experimental Procedures

### 6.1 Experiment 1: Decay Rate Comparison

**Hypothesis:** λ = 0.002 will provide optimal balance between recency and salience.

**Procedure:**

1. Seed 8 memories with fixed timestamps
2. For each λ ∈ {0.0005, 0.001, 0.002, 0.005, 0.01}:
   - Embed Query 1
   - Search Qdrant for top 8 memories (cosine similarity)
   - For each memory:
     - Calculate decay: `exp(-λ × age_days)`
     - Calculate activation: `similarity × decay × salience`
   - Sort by activation
   - Record top 3 memories
3. Compare rankings across λ values

**Success Criteria:**

- At low λ (0.0005, 0.001): Old high-salience memories dominate
- At λ = 0.002: Recent relevant memories win
- At high λ (0.005, 0.01): Only very recent memories accessible

**Data Collected:**

- For each of 5 λ values × 8 memories = 40 activation scores
- Top 3 rankings for each λ
- Full activation arrays for detailed analysis

### 6.2 Experiment 2: Salience × Decay Interaction

**Hypothesis:** High salience can compensate for temporal decay.

**Procedure:**

1. Fix λ = 0.002 (optimal from Experiment 1)
2. Embed Query 2 ("system problems and emergencies")
3. Search Qdrant for all 8 memories
4. Calculate activation for each: `similarity × decay × salience`
5. Compare:
   - System outage (180d, salience 2.5) vs. hallway chat (2d, salience 0.3)
   - Quantify how much salience compensates for decay

**Success Criteria:**

- System outage ranks #1 despite being 90× older
- Low-salience recent memories rank low despite recency

**Data Collected:**

- Activation scores for all 8 memories
- Ranking by activation
- Breakdown: similarity, decay, salience contributions

### 6.3 Experiment 3: Temporal Progression

**Hypothesis:** Decay follows exponential curve matching Ebbinghaus findings.

**Procedure:**

1. Fix λ = 0.002, salience = 1.5
2. Embed Query 3 ("demonstration to colleagues")
3. Get similarity score from Qdrant (fixed value)
4. For each time point t ∈ {0, 1, 7, 30, 90, 180, 365, 730} days:
   - Calculate decay: `exp(-0.002 × t)`
   - Calculate activation: `similarity × decay × salience`
   - Calculate retention %: `decay × 100`
   - Calculate loss: `100 - retention`
5. Plot decay curve (via data table)

**Success Criteria:**

- Rapid initial loss (0-30 days)
- Gradual plateau (180-730 days)
- Never reaches zero (always some residual)

**Data Collected:**

- 8 time points with decay, retention%, activation
- Loss from baseline at each point

---

## 7. Activation Calculation Details

### 7.1 Mathematical Formula

```
activation = similarity × decay × salience
```

Where:

- **similarity** ∈ [0, 1]: Cosine similarity from Qdrant search
- **decay** ∈ [0, 1]: `exp(-λ × age_days)`
- **salience** ∈ [0, ∞): User-defined importance weight (typically 0.3-2.5)

### 7.2 Component Analysis

**Similarity (Semantic Relevance):**

```python
similarity = cosine_similarity(query_vector, memory_vector)
```

- Calculated by Qdrant during search
- Uses L2-normalized 1024-dim vectors
- Range: [-1, 1], but typically [0, 1] for embeddings

**Decay (Temporal Degradation):**

```python
age_days = (now - stored_at).days
decay = math.exp(-lambda * age_days)
```

- Exponential decay following Ebbinghaus curve
- λ = 0.002 means ~5.8% loss after 30 days
- Never reaches exactly zero (exp approaches but doesn't hit 0)

**Salience (Importance Weight):**

- Manually assigned based on event significance
- Normal events: 1.0 (baseline)
- Trivial: 0.3-0.8 (hallway chat, routine standup)
- Important: 1.2-1.5 (demos, strategic meetings)
- Critical: 2.0-3.0 (emergencies, major incidents)

### 7.3 Example Calculation

**Memory:** System outage (ID 5)

- **Days ago:** 180
- **Salience:** 2.5
- **Query:** "system problems and emergencies"

**Steps:**

1. Embedding similarity (from Qdrant): 0.6773
2. Decay: `exp(-0.002 × 180) = exp(-0.36) = 0.6977`
3. Activation: `0.6773 × 0.6977 × 2.5 = 1.1814`

**Interpretation:** Despite 70% temporal decay (30% lost), high salience (2.5×) amplifies activation to >1.0, making it top-ranked memory.

---

## 8. Data Collection and Storage

### 8.1 Output Format

All results saved to `validation_results.json`:

```json
{
  "timestamp": "2025-10-02T11:27:17.459481+00:00",
  "experiments": [
    {
      "name": "decay_rate_comparison",
      "data": {
        "query": "...",
        "lambda_comparisons": [
          {
            "lambda": 0.002,
            "top_3_memories": [...],
            "all_activations": [...]
          }
        ]
      }
    }
  ]
}
```

### 8.2 Data Fields

For each memory-query-lambda combination:

- `id`: Memory ID (1-8)
- `text_preview`: First 60 chars of memory text
- `days_ago`: Age in days (for analysis)
- `category`: Memory category string
- `similarity`: Cosine similarity score (float)
- `salience`: Importance weight (float)
- `decay`: Temporal decay weight (float)
- `activation`: Final activation score (float)

### 8.3 Reproducibility

To reproduce experiments:

```bash
# 1. Ensure Ollama is running with BGE-M3
ollama pull bge-m3

# 2. Start infrastructure
cd convai_narrative_memory_poc
docker compose up -d qdrant

# 3. Run validation
docker compose build tools
docker compose run --rm tools python /app/convai_narrative_memory_poc/tools/validation_experiments.py

# 4. Results in validation_results.json
cat /tmp/validation_output.txt  # If captured to file
```

**Expected Runtime:** ~2-3 minutes

- Embedding generation: ~30 seconds (8 memories + 3 queries)
- Qdrant operations: ~1 second (searches very fast)
- Calculation loops: <1 second (pure Python math)

---

## 9. Controls and Limitations

### 9.1 Controlled Variables

To ensure valid comparisons:

- Same embedding model (BGE-M3) for all memories and queries
- Same Qdrant collection (recreated fresh each run)
- Same experiment timestamp (all age calculations from fixed reference point)
- Same memory corpus (8 identical memories across all tests)

### 9.2 Sources of Variation

**Minimal variation:**

- Ollama embedding generation is deterministic (same text → same vector)
- Qdrant cosine similarity is deterministic (same vectors → same score)
- Decay calculation is deterministic (pure math)

**No randomness in experiments** (fully reproducible).

### 9.3 Limitations

1. **Synthetic corpus**: Not real conversational data, may not capture full complexity
2. **Small sample size**: 8 memories (sufficient for proof-of-concept, not statistical power)
3. **Single domain**: Professional/work context only (no personal/emotional events)
4. **Fixed queries**: Only 3 test queries (limited coverage of semantic space)
5. **No user study**: Activation scores not validated by human perception
6. **Static test**: Doesn't test dynamic memory updates or recall patterns over time

### 9.4 Future Validation Needs

For production deployment:

- Larger corpus (100+ memories)
- Real conversational data from Virtual Human interactions
- User studies comparing perceived realism across λ values
- Longitudinal testing (memory system running for weeks/months)
- Cross-lingual validation (BGE-M3 supports multilingual, not tested yet)

---

## 10. Statistical Analysis

### 10.1 Descriptive Statistics

**Similarity Scores (Query 1):**

- Range: 0.4093 - 0.6045
- Mean: 0.5360
- Demonstrates moderate semantic overlap across memories

**Decay Weights (λ=0.002, across all ages):**

- Range: 0.5827 (270d) - 0.998 (1d)
- Mean: 0.8856
- Shows expected exponential distribution

**Activation Scores (λ=0.002, Query 1):**

- Range: 0.1729 - 0.7834
- Winner: ID 1 (demo, 1 day old, 0.7834)
- Loser: ID 4 (hallway, 2 days old, 0.1729) — low salience penalty

### 10.2 Comparative Analysis

**Effect of λ on Top Memory:**

| λ         | Top Memory    | Activation | % Difference from λ=0.002 |
| --------- | ------------- | ---------- | ------------------------- |
| 0.0005    | System outage | 0.9812     | +25.3%                    |
| 0.001     | System outage | 0.8968     | +14.5%                    |
| **0.002** | **Demo**      | **0.7834** | **0%** (baseline)         |
| 0.005     | Demo          | 0.7810     | -0.3%                     |
| 0.01      | Demo          | 0.7771     | -0.8%                     |

**Interpretation:** λ affects activation magnitude, but more importantly changes **ranking**. At 0.0005/0.001, different memory wins entirely.

---

## 11. Conclusion

This experimental methodology provides:

1. **Reproducible validation** of Ebbinghaus curve implementation
2. **Quantitative evidence** for optimal λ = 0.002
3. **Proof** that multi-factor activation (similarity × decay × salience) works as designed
4. **Foundation** for future research (12-week proposal)

All code, data, and results are open-source and fully documented for peer review and replication.

---

## Appendix: Code Excerpts

### A. Memory Seeding

```python
def seed_test_memories(self, collection_name: str = "validation_anchors") -> List[Dict]:
    now = dt.datetime.now(dt.timezone.utc)

    memories = [
        {
            "id": 1,
            "text": "Demonstrated Virtual Human to 12 Fontys colleagues...",
            "days_ago": 1,
            "salience": 1.5,
            "category": "recent_high_salience",
        },
        # ... 7 more memories
    ]

    points = []
    for mem in memories:
        stored_at = now - dt.timedelta(days=mem["days_ago"])
        embedding = get_embedding(mem["text"])  # BGE-M3 via Ollama

        points.append(
            models.PointStruct(
                id=mem["id"],
                vector=embedding,
                payload={
                    "text": mem["text"],
                    "stored_at": stored_at.isoformat(),
                    "salience": mem["salience"],
                    "category": mem["category"],
                    "days_ago": mem["days_ago"],
                },
            )
        )

    self.client.upsert(collection_name=collection_name, wait=True, points=points)
    return memories
```

### B. Activation Calculation

```python
def activate(self, similarity: float, stored_at: dt.datetime,
             salience: float, now: dt.datetime, lam: float) -> float:
    """Multi-factor activation score"""
    age_days = (now - stored_at).days
    decay = math.exp(-lam * age_days)
    return similarity * decay * salience
```

### C. Experiment Execution

```python
def experiment_1_decay_rates(self, collection_name: str) -> Dict:
    lambda_values = [0.0005, 0.001, 0.002, 0.005, 0.01]
    query_embedding = get_embedding("Tell me about the demonstration...")

    results = {"query": query_text, "lambda_comparisons": []}

    for lam in lambda_values:
        search_results = self.client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=8
        )

        activations = []
        for hit in search_results:
            activation = self.activate(
                hit.score,
                dt.datetime.fromisoformat(hit.payload["stored_at"]),
                hit.payload["salience"],
                now,
                lam
            )
            activations.append({
                "id": hit.id,
                "activation": activation,
                # ... other fields
            })

        activations.sort(key=lambda x: x["activation"], reverse=True)
        results["lambda_comparisons"].append({
            "lambda": lam,
            "top_3_memories": activations[:3],
        })

    return results
```

---

**Document Prepared By:** ConvAI Narrative Memory Research Team  
**Contact:** Lonn van Bokhorst, Coen Crombach  
**Institution:** Mindlabs  
**License:** MIT (open-source)
