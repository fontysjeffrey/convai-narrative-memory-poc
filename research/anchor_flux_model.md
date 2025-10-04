# The Anchor-and-Flux Memory Model

**Conceptual Foundation for Virtual Human Identity**

---

## Executive Summary

The **Anchor-and-Flux Model** is a paradigm shift in how virtual humans remember and maintain identity. Instead of relying on fixed personality traits (brittle, forgetful, hard to scale), we propose **identity emerging from stories over time**:

- **Anchors** = Durable, factual event memories (the "what happened")
- **Flux** = Living retellings that adapt to context while staying coherent (the "how it's remembered")

This document explains the conceptual model, its implementation in our PoC, and how it differs from traditional approaches.

---

## 1. The Problem with Traditional Virtual Humans

### 1.1 Fixed Personality Traits

Most virtual humans simulate "personality" with fixed trait sliders:

```
personality = {
  "openness": 0.7,
  "conscientiousness": 0.8,
  "extraversion": 0.6,
  "agreeableness": 0.9,
  "neuroticism": 0.3
}
```

**Problems:**

- ❌ **Brittle**: Doesn't capture how real people evolve through experiences
- ❌ **Forgetful**: No connection to actual events or conversations
- ❌ **Hard to scale**: Requires manual tuning for each use case
- ❌ **Inauthentic**: Users can sense the "sliders underneath"

### 1.2 Perfect Recall Systems

Some systems (e.g., basic RAG) store every conversation:

```
memory_db = {
  "2025-10-01": "User asked about weather",
  "2025-10-02": "User mentioned their dog",
  "2025-10-03": "Discussed project deadline"
  ...
}
```

**Problems:**

- ❌ **Robotic**: Remembers everything with perfect fidelity
- ❌ **No prioritization**: Trivial and important events treated equally
- ❌ **No natural forgetting**: Unlike humans, never fades or becomes fuzzy

---

## 2. The Anchor-and-Flux Paradigm

### 2.1 Core Concept

**Human identity emerges from stories, not traits.**

When you ask someone "Who are you?", they don't list trait scores—they tell stories:

- "I'm the person who quit their job to travel Europe"
- "I'm someone who values family over career"
- "I once stayed up 48 hours to finish a project I believed in"

These stories:

1. **Anchor** the person in factual events (what objectively happened)
2. **Flux** in how they're told (emphasis, emotion, detail changes with context)

### 2.2 Two-Layer Architecture

```
┌─────────────────────────────────────────────────────┐
│                    FLUX LAYER                       │
│  (Living retellings - adapt to context)             │
│                                                     │
│  "Yesterday I demoed to colleagues - energizing!"  │
│  "Last week we showed the system to Fontys folks"  │
│  "Some time back we did a demo... fuzzy now"      │
└─────────────────────────────────────────────────────┘
                          ↑
                    retells with
                    context/time
                          ↓
┌─────────────────────────────────────────────────────┐
│                   ANCHOR LAYER                      │
│  (Durable event-facts - persist unchanged)         │
│                                                     │
│  Event: "Demonstrated Virtual Human to 12 Fontys   │
│          colleagues in R10 at 14:30. Engaging Q&A  │
│          about ethics and data retention."         │
│  When: 2025-10-01T14:30:00Z                        │
│  Salience: 1.5 (high importance)                   │
└─────────────────────────────────────────────────────┘
```

**Key Insight:** The **anchor never changes** (factual truth), but the **flux adapts** (how it's remembered/told).

---

## 3. What Are Anchors?

### 3.1 Definition

**Anchors** are short, durable event-facts stored in plain language.

**Characteristics:**

- ✅ **Factual**: "We demoed at Fontys" (not "I felt excited")
- ✅ **Specific**: Includes key details (who, what, where, when)
- ✅ **Immutable**: Once stored, the core facts don't change
- ✅ **Tagged**: Metadata for importance (salience), time, context

### 3.2 Anchor Structure

```python
{
    "anchor_id": "uuid",
    "text": "Demonstrated Virtual Human to 12 Fontys colleagues in R10",
    "stored_at": "2025-10-01T14:30:00Z",
    "salience": 1.5,  # Importance weight (0.3 = trivial, 2.5 = critical)
    "meta": {
        "tags": ["demo", "fontys", "public-speaking"],
        "participants": ["12 colleagues"],
        "location": "R10"
    },
    "embedding": [0.23, -0.45, ..., 0.67]  # Semantic vector
}
```

### 3.3 Why Anchors Are Durable

**Philosophical reason:** Facts don't change. If you demoed at Fontys on Oct 1st, that's eternally true.

**Practical reason:** Immutable anchors prevent:

- Contradictions ("Wait, yesterday you said...")
- Drift into fantasy ("I once saved the world from aliens")
- Loss of continuity ("Who am I again?")

**Critical architectural principle:** Retellings (flux) must never be stored back as anchors.

- ❌ Don't: Persist reteller output as new anchors or overwrite originals
- ❌ Don't: Treat summarized or refined retellings as upgraded anchor facts
- ✅ Do: Keep flux strictly transient—generate it only when responding
- ✅ Do: Regenerate every retelling directly from the immutable anchor set

Violating this pollutes the anchor pool with derived content, causes "telephone game" drift, and erodes the factual ground truth that stabilizes identity.

### 3.4 Anchor Examples

| Type            | Example                             | Salience | Why Stored                     |
| --------------- | ----------------------------------- | -------- | ------------------------------ |
| **Routine**     | "Weekly standup meeting on Oct 1st" | 0.8      | Provides temporal context      |
| **Significant** | "Launched new feature to 500 users" | 1.3      | Milestone, shapes identity     |
| **Critical**    | "System outage affecting 50+ users" | 2.5      | Crisis event, highly memorable |
| **Trivial**     | "Hallway chat about weather"        | 0.3      | Background noise, fades fast   |

---

## 4. What Is Flux?

### 4.1 Definition

**Flux** is the adaptive retelling of anchors—how memories are narrated in different contexts and time frames.

**Characteristics:**

- ✅ **Adaptive**: Changes based on audience, mood, time elapsed
- ✅ **Grounded**: Always rooted in anchor facts (no hallucinations)
- ✅ **Natural**: Mimics how humans retell stories differently each time
- ✅ **Fuzzy with age**: Recent = detailed, old = vague
- ✅ **Transient**: Output-only narratives that are never persisted as anchors

### 4.2 Flux Mechanics

When recalling a memory, the system:

1. **Retrieves anchor** from vector database (semantic search + temporal decay)
2. **Calculates perceived age**: "yesterday" vs. "months ago" vs. "years back"
3. **Generates retelling** via LLM with context:
   - Anchor text (factual skeleton)
   - Perceived age (freshness vs. fuzziness)
   - Current context (who's asking? why? what mood?)

### 4.3 Example: Same Anchor, Different Flux

**Anchor (immutable):**

```
"Demonstrated Virtual Human to 12 Fontys colleagues in R10 at 14:30.
Engaging Q&A about ethics and data retention."
Stored: 2025-10-01T14:30:00Z
```

**Flux 1 (next day, to colleague):**

```
"Yesterday we demoed to a dozen Fontys folks in R10—really energizing!
They peppered us with sharp questions about ethics, especially around data retention.
I think we nailed the demo."
```

- **Style**: Enthusiastic, detailed
- **Details**: Exact room, time, specific topics
- **Emotion**: Positive ("energizing", "nailed it")

**Flux 2 (one week later, to manager):**

```
"Last week we showed the Virtual Human system to Fontys colleagues.
The Q&A focused heavily on ethical considerations, which we addressed well."
```

- **Style**: Professional, summarized
- **Details**: Less specific ("last week", no room number)
- **Emotion**: Neutral, factual

**Flux 3 (9 months later, casual conversation):**

```
"We did a demo at Fontys some months back—there was a good discussion around
ethics and memory, though the specifics are a bit hazy now."
```

- **Style**: Casual, uncertain
- **Details**: Vague ("some months back", no room/time)
- **Emotion**: Reflective, acknowledging fuzziness

**Key Insight:** The **anchor** (12 colleagues, R10, ethics Q&A) persists, but the **telling** adapts naturally.

---

## 5. How They Work Together

### 5.1 The Memory Lifecycle

```
1. Experience → ANCHOR
   Event happens → Stored as factual anchor

2. ANCHOR → Embedding
   Text converted to semantic vector (searchable)

3. Query → Retrieval
   "What do you remember about demos?"
   → Semantic search finds relevant anchors
   → Temporal decay weights by age
   → Salience boosts important events

4. Retrieved Anchors → FLUX
   LLM receives:
   - Anchor text(s)
   - Perceived age(s)
   - Current context
   → Generates natural retelling

5. FLUX → Response
   "Yesterday we demoed at Fontys..." (fresh)
   "Some time back we showed..." (fuzzy)
```

### 5.2 Multi-Factor Activation

Not all anchors are equal! Retrieval uses:

```
activation = similarity × decay × salience
```

**Similarity** (semantic relevance):

- How well does the query match the anchor?
- "Tell me about demos" → High match for demo anchor

**Decay** (temporal forgetting):

- How old is the memory?
- Recent (1 day): decay = 0.998 (almost no loss)
- Old (270 days): decay = 0.583 (significant fading)

**Salience** (importance):

- How significant was the event?
- Critical outage (2.5×): Boosted even if old
- Weather chat (0.3×): Suppressed even if recent

**Example:**

```
Query: "system problems"
Anchor 1: System outage (180 days old, salience 2.5)
  → similarity: 0.68, decay: 0.70, salience: 2.5
  → activation: 1.18

Anchor 2: Hallway weather chat (2 days old, salience 0.3)
  → similarity: 0.44, decay: 0.996, salience: 0.3
  → activation: 0.13

Result: Old critical event outranks recent trivial chat!
```

---

## 6. Implementation in Our PoC

### 6.1 Anchor Layer (Implemented)

**Technology Stack:**

- **Storage**: Qdrant vector database
- **Embeddings**: BGE-M3 (1024-dim multilingual)
- **Format**: JSON payload with metadata

**What's Stored:**

```python
{
    "anchor_id": uuid,
    "text": "factual event description",
    "stored_at": ISO timestamp,
    "salience": float (0.3 - 2.5),
    "meta": {tags, participants, location, etc.},
    "embedding": 1024-dim vector
}
```

### 6.2 Flux Layer (Implemented)

**Technology Stack:**

- **Retrieval**: Resonance worker (semantic search + temporal decay)
- **Retelling**: Reteller worker (LLM-based regeneration)
- **LLMs**: Phi4, Qwen3, Llama3 (Ollama) or GPT-4o-mini (OpenAI)

**Process:**

1. **Resonance** retrieves anchors, calculates activation, adds "perceived age"
2. **Reteller** receives "beats" (anchor + age context)
3. **LLM prompt**:

   ```
   I'm recalling these moments; each ends with how long ago it feels:
   - [anchor text] (yesterday)
   - [anchor text] (9 months ago)

   Retell concisely like a human memory—fewer crisp details when older.
   ```

4. **Output**: Natural, age-appropriate narrative

### 6.3 Temporal Decay (Ebbinghaus Curve)

**Formula:** `decay = exp(-λ × days)`

**Default:** λ = 0.002

- 1 day: 99.8% retention
- 30 days: 94.2% retention
- 180 days: 69.8% retention
- 1 year: 48.2% retention
- 2 years: 23.2% retention

**Why this matters:**

- Mimics human forgetting curve (rapid initial loss → gradual plateau)
- Ensures old memories fade but never completely disappear
- Allows important old events (high salience) to stay accessible

---

## 7. Why This Model Works

### 7.1 Psychological Realism

**Humans don't have perfect memory:**

- We forget details but remember gist
- Recent events are vivid, old ones fuzzy
- Significant events (weddings, crises) resist forgetting
- Trivial events (what you ate Tuesday) fade fast

**Our model replicates this:**

- Anchors = gist (facts persist)
- Flux = fuzziness (details fade with time)
- Salience = emotional weight (crisis > lunch)
- Decay = natural forgetting (exponential curve)

### 7.2 Continuity Without Rigidity

**Problem with fixed traits:**

```
"I am 70% extraverted" ← Who talks like this?
```

**Our approach:**

```
"I'm the person who demoed at Fontys—that was intense!"
"I once dealt with a major system outage, stressful but learned a lot."
```

→ Identity emerges from stories, not sliders

**Benefits:**

- ✅ **Authentic**: Sounds like a real person
- ✅ **Dynamic**: Identity evolves through experiences
- ✅ **Coherent**: Same factual anchors = consistent "who I am"
- ✅ **Natural**: Adapts telling to context without losing core

### 7.3 Scalability

**Fixed traits require:**

- Manual tuning per use case
- Predicting all possible situations
- Brittle rules ("If user angry, reduce agreeableness by 0.2")

**Anchor-and-flux requires:**

- Just store what happens (events → anchors)
- Let LLM adapt retelling to context (flux)
- No manual rules needed (emergent behavior)

---

## 8. Research Validation

### 8.1 What We've Proven (PoC)

✅ **Anchors persist correctly:**

- Stored in vector DB with timestamps
- Retrievable via semantic search
- Maintain factual consistency

✅ **Temporal decay works:**

- Exponential forgetting curve (λ=0.002 optimal)
- Recent memories dominate naturally
- Old significant events stay accessible

✅ **Flux adapts naturally:**

- LLM retellings reflect perceived age
- Recent: detailed, specific
- Old: vague, "a bit hazy"

✅ **Multi-factor activation:**

- Salience counteracts decay (flashbulb memories)
- Semantic relevance prioritizes pertinent memories
- System feels "human-like" not robotic

### 8.2 What We'll Research (12 Weeks)

**Weeks 1-3: Multi-Agent Anchors**

- How do multiple agents share anchors?
- "I remember" vs. "I heard from X" distinction
- Rumor propagation through shared memory pool

**Weeks 4-6: Character-Driven Flux**

- Same anchor, different personalities → different retellings
- Optimistic character: emphasizes positive aspects
- Anxious character: remembers threats/risks
- Mood modulation: angry → selective negative recall

**Weeks 7-8: Security of Anchors**

- Prevent memory injection attacks
- Audit who accessed/modified anchors
- GDPR-compliant memory deletion

**Weeks 9-10: Scalability**

- 100+ agents, 100k+ anchors
- Real-time retrieval (<500ms)
- Horizontal scaling validation

---

## 9. Comparison to Other Approaches

### 9.1 vs. Traditional RAG

| Aspect         | Traditional RAG | Anchor-and-Flux               |
| -------------- | --------------- | ----------------------------- |
| **Storage**    | Raw documents   | Factual anchors + metadata    |
| **Retrieval**  | Similarity only | Similarity × decay × salience |
| **Output**     | Raw text chunks | Age-aware adaptive retelling  |
| **Forgetting** | None            | Ebbinghaus exponential decay  |
| **Identity**   | None            | Emerges from story collection |

### 9.2 vs. Memory Networks

| Aspect               | Memory Networks      | Anchor-and-Flux           |
| -------------------- | -------------------- | ------------------------- |
| **Architecture**     | Neural (end-to-end)  | Hybrid (vectors + LLM)    |
| **Interpretability** | Black box            | Human-readable anchors    |
| **Temporal decay**   | None                 | Explicit Ebbinghaus model |
| **Retelling**        | Fixed representation | Dynamic LLM generation    |

### 9.3 vs. Fixed Personality

| Aspect              | Fixed Traits     | Anchor-and-Flux           |
| ------------------- | ---------------- | ------------------------- |
| **Identity source** | Manual sliders   | Emergent from experiences |
| **Consistency**     | Rigid            | Flexible but grounded     |
| **Adaptability**    | Brittle rules    | Natural LLM adaptation    |
| **User perception** | "Feels scripted" | "Feels authentic"         |

---

## 10. Future Directions

### 10.1 Emotional Anchors

Currently, salience is a simple float (0.3 - 2.5). Future:

```python
{
    "anchor_id": uuid,
    "text": "System outage...",
    "emotion": {
        "valence": -0.8,  # Negative experience
        "arousal": 0.9,   # High intensity
        "dominance": 0.3  # Felt out of control
    },
    "salience": 2.5
}
```

**Impact on flux:**

- Negative memories: More cautious retelling
- High-arousal: More vivid detail retention
- Low-dominance: "It happened to me" (passive voice)

### 10.2 Memory Reconsolidation

Humans strengthen memories when recalling them. Future:

```python
def on_recall(anchor_id):
    # Reactivate the memory
    anchor = db.get(anchor_id)
    anchor["last_accessed"] = now()
    anchor["access_count"] += 1

    # Option 1: Reset temporal decay (controversial!)
    anchor["stored_at"] = now()  # Memory feels "fresh" again

    # Option 2: Boost salience slightly
    anchor["salience"] *= 1.1  # Cap at 3.0
```

**Research question:** Does this improve continuity or cause unrealistic "stickiness"?

### 10.3 Forgetting vs. Archiving

Currently, old memories fade but never vanish (exp never reaches 0). Future:

```python
if decay < 0.1 and access_count == 0:
    # Archive to cold storage
    move_to_archive(anchor_id)
```

**Benefits:**

- Performance (smaller active set)
- Privacy (old data not easily accessible)

**Risk:**

- Loss of long-term continuity ("I used to remember that...")

### 10.4 Cross-Lingual Flux

BGE-M3 embeddings are multilingual (100+ languages). Future:

```
Anchor (stored in English):
  "Demonstrated Virtual Human at Fontys"

Query (in Dutch):
  "Vertel me over de demonstratie"

Flux (in Dutch):
  "Gisteren hebben we de Virtual Human gedemonstreerd bij Fontys..."
```

**Research question:** Does semantic similarity hold across languages? Does LLM retelling quality vary?

---

## 11. Conclusion

The **Anchor-and-Flux Model** provides a psychologically grounded, technically scalable approach to virtual human memory:

**Anchors** = Durable facts (what happened)  
**Flux** = Adaptive retellings (how it's remembered)

**Benefits:**

- ✅ **Authentic**: Identity emerges from stories, not sliders
- ✅ **Realistic**: Mimics human forgetting and retelling
- ✅ **Scalable**: No manual trait tuning required
- ✅ **Coherent**: Factual anchors prevent contradictions
- ✅ **Flexible**: Flux adapts to context naturally

**Implementation:**

- Anchors → Qdrant (vector DB with temporal metadata)
- Flux → LLM (context-aware retelling)
- Glue → Kafka (event-driven microservices)

**Validated:**

- λ = 0.002 optimal for conversational memory
- Multi-factor activation works (similarity × decay × salience)
- LLM retellings reflect perceived age naturally

**Next Steps:**

- Multi-agent shared/private anchors
- Character-driven flux (personality affects retelling)
- Security, scalability, platform integration

---

**Document Version:** 1.0  
**Date:** October 2, 2025  
**Authors:** Lonn van Bokhorst, Coen Crombach  
**Organization:** Mindlabs  
**Related Documents:** ARCHITECTURE.md, FORGETTING_CURVE.md, RESEARCH_PROPOSAL.md
