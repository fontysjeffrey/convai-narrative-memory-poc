# Resonance Worker Enhancement Plan

## Huidige Status Analyse

### Wat de Resonance worker nu doet:

**Core Functionaliteit:**
1. **Input**: Consumeert `recall-request` topic met:
   - Query text
   - Timestamp (`now`)
   - `top_k` (aantal memories om te vinden)
   - `session_id` (optioneel)
   - `ignore_anchor_ids` (optioneel)
   - `allow_session_matches` (optioneel)

2. **Processing Pipeline**:
   - Embed query text → vector
   - Semantic search in Qdrant (cosine similarity)
   - Filter anchors:
     - Exclude `ignore_anchor_ids`
     - Exclude session matches (als `allow_session_matches=False`)
     - Exclude very recent (<5 seconds old)
   - Dedupe by text (identical anchors)
   - Calculate activation: `similarity × decay × salience`
   - Sort by activation score
   - Apply diversity selection (voorkomt repetitieve results)
   - Calculate `perceived_age` (human-readable: "yesterday", "9 months ago")

3. **Output**: Publiceert `recall-response` met beats array

### Huidige Features:

✅ **Multi-factor activation**: `similarity × decay × salience`  
✅ **Temporal decay**: Ebbinghaus curve (`exp(-λ × days)`, λ=0.002)  
✅ **Diversity selection**: Voorkomt te vergelijkbare memories  
✅ **Session filtering**: Kan session memories uitsluiten  
✅ **Recent memory filtering**: <5 seconden oude memories worden genegeerd  
✅ **Tag-based diversity bonus**: Nieuwe tags krijgen bonus  
✅ **Configurable parameters**: Via environment variables

### Wat ontbreekt (uit research proposal & code analyse):

❌ **Mood-aware memory selection**: Mood beïnvloedt welke memories worden geselecteerd  
❌ **Emotional filtering**: Filter op basis van emotional valence (positive/negative)  
❌ **Multi-agent context**: Shared vs. private memories  
❌ **Performance optimization**: Caching, batch processing  
❌ **Alternative decay functions**: Alleen exponential, geen power-law of custom  
❌ **Memory reconsolidation**: Recent accessed memories kunnen "fresher" worden  
❌ **Temporal clustering**: Memories dicht bij elkaar in tijd kunnen worden gegroepeerd  
❌ **Query expansion**: Query kan worden uitgebreid met synoniemen/related terms  
❌ **Metadata filtering**: Filter op tags, participants, location, etc.  
❌ **Activation threshold**: Minimum activation score om te worden meegenomen

---

## Enhancement Doelstellingen

### 1. Mood-Aware Memory Selection (Priority: HIGH)

**Wat het moet doen:**
- Resonance ontvangt mood/emotional state in recall request
- Selecteert memories die mood matchen:
  - Happy mood → meer positieve memories
  - Sad/angry mood → meer negatieve memories (of neutrale)
  - Anxious mood → meer memories met hoge arousal

**Implementatie:**
```python
# In recall-request payload:
{
    "request_id": "...",
    "query": "...",
    "mood": {
        "valence": 0.7,  # -1.0 (sad) to 1.0 (happy)
        "arousal": 0.5,  # 0.0 (calm) to 1.0 (excited)
        "current_state": "happy"
    }
}

# In resonance:
def mood_boost(anchor, mood):
    """Boost activation if anchor emotion matches mood"""
    anchor_emotion = anchor.get("emotion", {})
    if not anchor_emotion:
        return 1.0  # No boost if no emotion data
    
    # Valence matching
    anchor_valence = anchor_emotion.get("valence", 0.0)
    mood_valence = mood.get("valence", 0.0)
    valence_match = 1.0 - abs(anchor_valence - mood_valence)  # Closer = higher
    
    # Boost activation if valence matches
    boost = 1.0 + (valence_match * 0.2)  # Up to 20% boost
    return min(boost, 1.3)  # Cap at 30% boost
```

**Voorbeeld:**
```
Query: "Tell me about good times"
Mood: {valence: 0.8, current_state: "happy"}

Result: Positieve memories krijgen boost, negatieve worden onderdrukt
```

### 2. Emotional Filtering (Priority: MEDIUM)

**Wat het moet doen:**
- Filter memories op basis van emotional content
- Optioneel: alleen positieve, alleen negatieve, of alle

**Implementatie:**
```python
# In recall-request:
{
    "emotion_filter": {
        "valence_min": -1.0,  # Optional
        "valence_max": 1.0,   # Optional
        "arousal_min": 0.0,   # Optional
        "arousal_max": 1.0    # Optional
    }
}

# In resonance filtering:
if emotion_filter:
    anchor_emotion = anchor.get("emotion", {})
    if anchor_emotion:
        valence = anchor_emotion.get("valence", 0.0)
        if valence < emotion_filter.get("valence_min", -1.0):
            continue  # Skip this anchor
        if valence > emotion_filter.get("valence_max", 1.0):
            continue
```

### 3. Multi-Agent Context (Priority: HIGH - uit research proposal)

**Wat het moet doen:**
- Onderscheid tussen "I remember" (eigen memories) vs "I heard from X" (shared memories)
- Support voor shared memory pools tussen agents
- Private vs. public memory filtering

**Data Structure:**
```python
# Anchor metadata:
{
    "meta": {
        "agent_id": "agent-123",  # Wie heeft deze memory?
        "visibility": "private" | "shared" | "public",
        "shared_with": ["agent-456", "agent-789"]  # Als shared
    }
}

# Recall request:
{
    "agent_id": "agent-123",
    "include_shared": True,  # Include memories from other agents?
    "shared_agents": ["agent-456"]  # Specific agents to include
}
```

**Implementatie:**
```python
def filter_by_agent_context(anchor, agent_id, include_shared, shared_agents):
    """Filter anchors based on agent ownership"""
    meta = anchor.get("meta", {})
    anchor_agent = meta.get("agent_id")
    visibility = meta.get("visibility", "private")
    
    # Own memories always included
    if anchor_agent == agent_id:
        return True
    
    # Shared memories
    if include_shared and visibility == "shared":
        if not shared_agents or anchor_agent in shared_agents:
            return True
    
    # Public memories
    if visibility == "public":
        return True
    
    return False
```

### 4. Performance Optimization (Priority: MEDIUM)

**Wat het moet doen:**
- Caching van query embeddings
- Caching van diversity calculations
- Batch processing voor meerdere queries
- Connection pooling voor Qdrant

**Implementatie:**
```python
# Query embedding cache
_query_embedding_cache = {}
def get_cached_query_embedding(query):
    if query in _query_embedding_cache:
        return _query_embedding_cache[query]
    embedding = get_embedding(query)
    _query_embedding_cache[query] = embedding
    return embedding

# Diversity calculation cache (per query + top_k)
_diversity_cache = {}
def get_cached_diversity_selection(scored, desired, query_hash):
    cache_key = (query_hash, desired, tuple(h.id for _, h in scored[:10]))
    if cache_key in _diversity_cache:
        return _diversity_cache[cache_key]
    result = select_diverse_scored(scored, desired, {})
    _diversity_cache[cache_key] = result
    return result
```

### 5. Alternative Decay Functions (Priority: LOW)

**Wat het moet doen:**
- Support voor verschillende decay functies:
  - Exponential (huidige)
  - Power-law
  - Custom per anchor type

**Implementatie:**
```python
DECAY_FUNCTION = os.getenv("RESONANCE_DECAY_FUNCTION", "exponential")

def decay_weight_exponential(stored_at_iso, now, lam=LAM):
    age_days = (now - stored).days
    return math.exp(-lam * age_days)

def decay_weight_power_law(stored_at_iso, now, alpha=0.5):
    age_days = (now - stored).days
    return 1.0 / (1.0 + age_days) ** alpha

def decay_weight(stored_at_iso, now):
    if DECAY_FUNCTION == "power_law":
        return decay_weight_power_law(stored_at_iso, now)
    return decay_weight_exponential(stored_at_iso, now)
```

### 6. Memory Reconsolidation (Priority: LOW - experimenteel)

**Wat het moet doen:**
- Wanneer een memory wordt opgehaald, kan deze "fresher" worden
- Simuleert menselijk geheugen: recall versterkt memory

**Implementatie:**
```python
# Option 1: Reset temporal decay (controversieel!)
def on_recall(anchor_id, now):
    anchor = get_anchor(anchor_id)
    # Reset stored_at to now (memory feels fresh again)
    anchor["stored_at"] = now.isoformat()
    update_anchor(anchor)

# Option 2: Boost salience slightly
def on_recall(anchor_id):
    anchor = get_anchor(anchor_id)
    anchor["salience"] = min(anchor["salience"] * 1.1, 3.0)  # Cap at 3.0
    update_anchor(anchor)
```

**Risico**: Kan leiden tot "sticky" memories die altijd worden opgehaald

### 7. Metadata Filtering (Priority: MEDIUM)

**Wat het moet doen:**
- Filter op tags, participants, location, etc.
- Nuttig voor context-aware recall

**Implementatie:**
```python
# In recall-request:
{
    "filters": {
        "tags": ["demo", "fontys"],  # Must have these tags
        "participants": ["colleagues"],
        "location": "R10",
        "date_range": {
            "start": "2025-01-01",
            "end": "2025-12-31"
        }
    }
}

# In resonance:
def matches_filters(anchor, filters):
    meta = anchor.get("meta", {})
    
    # Tag filtering
    if "tags" in filters:
        anchor_tags = set(meta.get("tags", []))
        required_tags = set(filters["tags"])
        if not required_tags.issubset(anchor_tags):
            return False
    
    # Date range filtering
    if "date_range" in filters:
        stored = parse_date(anchor["stored_at"])
        start = parse_date(filters["date_range"]["start"])
        end = parse_date(filters["date_range"]["end"])
        if not (start <= stored <= end):
            return False
    
    return True
```

### 8. Activation Threshold (Priority: LOW)

**Wat het moet doen:**
- Minimum activation score om te worden meegenomen
- Voorkomt zwakke memories in results

**Implementatie:**
```python
ACTIVATION_THRESHOLD = float(os.getenv("RESONANCE_ACTIVATION_THRESHOLD", "0.0"))

# In scoring:
for act, h in scored:
    if act < ACTIVATION_THRESHOLD:
        continue  # Skip weak memories
    # ... rest of processing
```

---

## Implementatie Volgorde

### Fase 1: Test Infrastructure (Week 1)

**Waarom eerst tests?**
- Resonance heeft complexe logica (diversity selection, activation calculation)
- Veel edge cases (lege queries, geen matches, verschillende decay scenarios)
- Tests maken refactoring veiliger
- Tests documenteren verwacht gedrag

**Wat we maken:**

1. **Unit Tests** (`tests/workers/resonance/test_resonance_units.py`):
   - `test_decay_weight()` - verschillende leeftijden, verschillende λ
   - `test_activation_calculation()` - similarity × decay × salience
   - `test_dedupe_hits_by_text()` - duplicate detection
   - `test_select_diverse_scored()` - diversity selection logic
   - `test_cosine_similarity()` - vector similarity
   - `test_human_age()` - age string formatting

2. **Integration Tests** (`tests/workers/resonance/test_resonance_integration.py`):
   - Mock Qdrant client
   - Mock Kafka consumer/producer
   - Test volledige flow: query → beats
   - Test filtering (session, ignore_ids, recent)
   - Test diversity selection met verschillende configuraties

3. **Test Data Fixtures** (`tests/fixtures/resonance_anchors.json`):
   - Voorbeeld anchors met verschillende:
     - Leeftijden (1 dag, 30 dagen, 180 dagen)
     - Salience levels (0.3, 1.0, 2.5)
     - Similarity scores
     - Tags en metadata

**Test Locatie:**
```
convai_narrative_memory_poc/
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── resonance_anchors.json
│   │   └── resonance_queries.json
│   └── workers/
│       ├── __init__.py
│       └── resonance/
│           ├── __init__.py
│           ├── test_resonance_units.py
│           └── test_resonance_integration.py
```

**Tools:**
- `pytest` voor test framework
- `pytest-mock` voor mocking (Qdrant, Kafka)
- `pytest-cov` voor coverage
- `faker` voor test data generation

---

### Fase 2: Mood-Aware Selection (Week 2-3)

**Stap 2.1: Data Structure Design**

```python
# Recall request uitbreiding:
{
    "request_id": "...",
    "query": "...",
    "mood": {  # NIEUW
        "valence": 0.7,
        "arousal": 0.5,
        "current_state": "happy"
    }
}
```

**Stap 2.2: Mood Boost Function**

```python
def calculate_mood_boost(anchor, mood):
    """Calculate activation boost based on mood matching"""
    if not mood:
        return 1.0  # No boost if no mood
    
    anchor_emotion = anchor.get("emotion", {})
    if not anchor_emotion:
        return 1.0  # No boost if anchor has no emotion
    
    # Valence matching
    anchor_valence = anchor_emotion.get("valence", 0.0)
    mood_valence = mood.get("valence", 0.0)
    
    # Closer valence = higher boost
    valence_diff = abs(anchor_valence - mood_valence)
    valence_match = 1.0 - valence_diff  # 0.0 (opposite) to 1.0 (same)
    
    # Boost: up to 20% for perfect match
    boost = 1.0 + (valence_match * 0.2)
    return min(boost, 1.3)  # Cap at 30%
```

**Stap 2.3: Integration**

```python
# In activation calculation:
decay = decay_weight(pl["stored_at"], now)
sal = float(pl.get("salience", 1.0))
mood_boost = calculate_mood_boost(pl, mood)  # NIEUW
act = float(h.score) * decay * sal * mood_boost  # NIEUW
```

**Stap 2.4: Testing**

- Test met verschillende moods
- Test met anchors zonder emotion (backward compatible)
- Test edge cases (extreme moods, missing mood data)

---

### Fase 3: Multi-Agent Context (Week 4-5)

**Stap 3.1: Data Structure**

```python
# Anchor metadata uitbreiding:
{
    "meta": {
        "agent_id": "agent-123",
        "visibility": "private" | "shared" | "public",
        "shared_with": ["agent-456"]
    }
}

# Recall request uitbreiding:
{
    "agent_id": "agent-123",  # Wie vraagt?
    "include_shared": True,
    "shared_agents": ["agent-456"]  # Optioneel: specifieke agents
}
```

**Stap 3.2: Filtering Logic**

```python
def filter_by_agent_context(anchor, agent_id, include_shared, shared_agents):
    """Filter based on agent ownership and visibility"""
    meta = anchor.get("meta", {})
    anchor_agent = meta.get("agent_id")
    visibility = meta.get("visibility", "private")
    
    # Own memories always included
    if anchor_agent == agent_id:
        return True
    
    # Shared memories
    if include_shared and visibility == "shared":
        shared_with = meta.get("shared_with", [])
        if agent_id in shared_with:
            if not shared_agents or anchor_agent in shared_agents:
                return True
    
    # Public memories (everyone can see)
    if visibility == "public":
        return True
    
    return False
```

**Stap 3.3: Integration**

- Filter anchors voordat activation calculation
- Update indexer om agent_id te ondersteunen (separate enhancement)

---

### Fase 4: Performance Optimization (Week 6)

**Stap 4.1: Caching**

- Query embedding cache
- Diversity selection cache (voor identieke queries)
- Qdrant connection pooling

**Stap 4.2: Benchmarking**

- Measure latency before/after
- Test met verschillende corpus sizes
- Memory usage monitoring

---

### Fase 5: Metadata Filtering (Week 7)

**Stap 5.1: Filter Structure**

```python
{
    "filters": {
        "tags": ["demo"],
        "date_range": {"start": "...", "end": "..."},
        "participants": ["colleagues"]
    }
}
```

**Stap 5.2: Qdrant Filter Integration**

- Gebruik Qdrant's native filtering (efficiënter dan post-filtering)
- Combineer met vector search

---

## Test Strategie

### Test Pyramid

```
        /\
       /  \      E2E Tests (1-2)
      /____\
     /      \    Integration Tests (10-15)
    /________\
   /          \  Unit Tests (30-40)
  /____________\
```

### Unit Tests (Bottom Layer)

**Focus**: Individuele functies, edge cases

```python
# test_resonance_units.py

def test_decay_weight_recent():
    """Test decay for recent memory (should be ~1.0)"""
    now = dt.datetime.now()
    stored = now - dt.timedelta(days=1)
    decay = decay_weight(stored.isoformat(), now)
    assert 0.99 < decay < 1.0

def test_decay_weight_old():
    """Test decay for old memory (should be <0.5)"""
    now = dt.datetime.now()
    stored = now - dt.timedelta(days=365)
    decay = decay_weight(stored.isoformat(), now)
    assert 0.4 < decay < 0.5

def test_activation_calculation():
    """Test activation = similarity × decay × salience"""
    similarity = 0.8
    decay = 0.9
    salience = 1.5
    activation = similarity * decay * salience
    assert activation == 1.08

def test_select_diverse_scored_empty():
    """Test diversity selection with empty input"""
    result = select_diverse_scored([], 3, {})
    assert result == []

def test_select_diverse_scored_identical():
    """Test diversity selection with identical anchors"""
    # Create 5 identical anchors
    # Should only return 1 (diversity prevents duplicates)
    pass

def test_dedupe_hits_by_text():
    """Test duplicate removal"""
    hits = [
        MockHit(text="Same text"),
        MockHit(text="Same text"),  # Duplicate
        MockHit(text="Different text")
    ]
    unique = dedupe_hits_by_text(hits)
    assert len(unique) == 2
```

### Integration Tests (Middle Layer)

**Focus**: Component interactions, Kafka flow

```python
# test_resonance_integration.py

def test_resonance_kafka_flow(mock_qdrant, mock_kafka):
    """Test full Kafka consumer → processing → producer flow"""
    # Setup: mock Qdrant with test anchors
    # Setup: mock Kafka consumer with test query
    # Execute: run resonance main loop
    # Assert: verify output beats structure

def test_resonance_session_filtering():
    """Test that session memories are filtered correctly"""
    # Create anchors with session_id
    # Query with allow_session_matches=False
    # Verify session anchors are excluded

def test_resonance_recent_filtering():
    """Test that very recent memories (<5s) are filtered"""
    # Create anchor from 3 seconds ago
    # Query
    # Verify anchor is excluded

def test_resonance_mood_boost():
    """Test mood-aware activation boost"""
    # Create anchor with emotion
    # Query with matching mood
    # Verify activation is boosted

def test_resonance_multi_agent():
    """Test multi-agent filtering"""
    # Create anchors from different agents
    # Query with agent_id and include_shared
    # Verify correct filtering
```

### E2E Tests (Top Layer)

**Focus**: Volledige system flow

```python
# test_resonance_e2e.py

def test_full_recall_lifecycle():
    """Test: anchor → recall request → beats"""
    # 1. Create anchor via indexer
    # 2. Request recall via resonance
    # 3. Verify beats are returned
    # 4. Check activation scores are reasonable
```

---

## File Structure

```
convai_narrative_memory_poc/
├── workers/
│   └── resonance/
│       ├── main.py                    # Huidige implementatie
│       ├── activation.py              # NIEUW: Activation calculations
│       ├── diversity.py               # NIEUW: Diversity selection (refactored)
│       ├── filtering.py              # NIEUW: All filtering logic
│       ├── mood.py                   # NIEUW: Mood-aware selection
│       └── multi_agent.py            # NIEUW: Multi-agent context
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── resonance_anchors.json
│   │   └── resonance_queries.json
│   └── workers/
│       └── resonance/
│           ├── test_resonance_units.py
│           ├── test_resonance_integration.py
│           └── test_resonance_e2e.py
└── research/
    └── resonance_enhancement_plan.md  # Dit document
```

---

## Success Criteria

### Fase 1 (Tests):
- ✅ >85% code coverage voor resonance
- ✅ Alle edge cases hebben tests
- ✅ Tests kunnen draaien zonder Docker/Kafka (mocked)

### Fase 2 (Mood-Aware):
- ✅ Mood beïnvloedt memory selection (statistisch significant)
- ✅ Backward compatible (geen mood = default behavior)
- ✅ Performance impact <10% latency increase

### Fase 3 (Multi-Agent):
- ✅ Agent filtering werkt correct
- ✅ Shared memories zijn toegankelijk
- ✅ Private memories blijven private

### Fase 4 (Performance):
- ✅ Query latency <100ms (p95) voor corpus <10k
- ✅ Memory usage stabiel (geen leaks)
- ✅ Caching reduces redundant calculations

### Fase 5 (Metadata Filtering):
- ✅ Filters werken correct
- ✅ Geen performance degradation

---

## Risico's & Mitigatie

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| Mood boost maakt selection te voorspelbaar | Medium | Test met diverse moods, human evaluation |
| Multi-agent filtering complex | High | Incremental implementation, extensive testing |
| Performance degradation door caching | Medium | Benchmark tests, cache size limits |
| Backward compatibility broken | High | Feature flags, default values, versioning |

---

## Volgende Stappen

1. **Review dit plan** met team (Lonn, Coen)
2. **Beslissen**: Starten met tests of direct features?
3. **Vergelijken met Reteller plan**: Welke worker eerst?
4. **Setup test infrastructure**: pytest, fixtures, CI/CD
5. **Begin met Fase 1**: Unit tests voor bestaande functies

---

## Vergelijking: Resonance vs. Reteller

| Aspect | Resonance | Reteller |
|--------|-----------|----------|
| **Complexiteit** | Hoog (diversity, activation) | Hoog (LLM, motifs) |
| **Testbaarheid** | Goed (deterministic logic) | Moeilijker (LLM output variabel) |
| **Impact** | Hoog (core memory retrieval) | Hoog (user-facing output) |
| **Dependencies** | Qdrant, Kafka | LLM APIs, Kafka |
| **Performance kritiek** | Ja (query latency) | Minder (async processing) |

**Aanbeveling**: Start met **Resonance** omdat:
- Logic is meer deterministic (makkelijker te testen)
- Performance is kritieker (query latency)
- Foundation voor andere features (mood, multi-agent)

---

**Document Version**: 1.0  
**Date**: 2025-11-21  
**Author**: Planning session met crocodeux

