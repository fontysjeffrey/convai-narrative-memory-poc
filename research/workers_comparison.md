# Workers Comparison & Decision Guide

## Overzicht van alle Workers

### 1. Indexer
**Rol**: Memory storage (write path)  
**Complexiteit**: Laag-Medium  
**Dependencies**: Qdrant, Kafka, Embedding models  
**Huidige Features**: ✅ Immutability check, ✅ Auto dimension handling, ✅ Embedding generation

**Mogelijke Enhancements**:
- Emotion detection bij anchor creation
- Automatic salience calculation
- Batch processing
- Validation rules

**Test Prioriteit**: Medium (relatief simpel, maar kritiek voor data integrity)

---

### 2. Resonance
**Rol**: Memory retrieval (read path) - "Psychological heart"  
**Complexiteit**: Hoog  
**Dependencies**: Qdrant, Kafka, Embedding models  
**Huidige Features**: ✅ Multi-factor activation, ✅ Diversity selection, ✅ Temporal decay, ✅ Session filtering

**Mogelijke Enhancements**:
- Mood-aware selection
- Multi-agent context
- Performance optimization
- Metadata filtering

**Test Prioriteit**: Hoog (complexe logica, performance kritiek)

---

### 3. Reteller
**Rol**: Narrative generation (output)  
**Complexiteit**: Hoog  
**Dependencies**: LLM APIs, Kafka  
**Huidige Features**: ✅ Multi-LLM support, ✅ Motif extraction, ✅ Forgetting simulation, ✅ Stub mode

**Mogelijke Enhancements**:
- Character-driven retelling
- Mood modulation
- Output validation
- Emotional anchors

**Test Prioriteit**: Hoog (user-facing, maar LLM output is variabel)

---

## Vergelijking: Resonance vs. Reteller

| Criterium | Resonance | Reteller | Winnaar |
|-----------|-----------|----------|---------|
| **Testbaarheid** | Deterministic logic, makkelijk te mocken | LLM output variabel, moeilijker | ✅ Resonance |
| **Performance Kritiek** | Query latency <100ms | Async, minder kritiek | ✅ Resonance |
| **Complexiteit** | Hoog (diversity, activation) | Hoog (LLM, motifs) | Gelijk |
| **Impact op Systeem** | Core retrieval (foundation) | User-facing output | Gelijk |
| **Dependencies** | Qdrant (lokaal) | LLM APIs (external) | ✅ Resonance |
| **Edge Cases** | Veel (lege queries, filters, etc.) | Veel (lege beats, LLM fails) | Gelijk |
| **Backward Compatibility** | Belangrijk (API contract) | Belangrijk (output format) | Gelijk |

---

## Aanbeveling: Start met Resonance

### Redenen:

1. **Beter testbaar**: 
   - Deterministic logic (geen LLM variabiliteit)
   - Makkelijker te mocken (Qdrant vs. LLM APIs)
   - Meer unit-testable functies

2. **Performance kritiek**:
   - Query latency is direct merkbaar voor users
   - Reteller is async (minder urgent)

3. **Foundation voor andere features**:
   - Mood-aware selection nodig voor Reteller mood modulation
   - Multi-agent context nodig voor character-driven retelling
   - Metadata filtering nuttig voor alle workers

4. **Minder external dependencies**:
   - Qdrant is lokaal (Docker)
   - LLM APIs zijn external (kosten, rate limits)

5. **Incremental value**:
   - Elke enhancement (mood, multi-agent) heeft directe impact
   - Reteller enhancements zijn afhankelijk van Resonance features

---

## Implementatie Volgorde Suggestie

### Week 1-2: Resonance Tests
- Unit tests voor alle core functies
- Integration tests voor Kafka flow
- Test fixtures en mocking setup

### Week 3-4: Resonance Mood-Aware
- Data structure design
- Mood boost implementation
- Testing en validation

### Week 5-6: Resonance Multi-Agent
- Agent context filtering
- Shared memory support
- Testing

### Week 7: Resonance Performance
- Caching implementation
- Benchmarking
- Optimization

### Week 8+: Reteller (als Resonance stabiel is)
- Character-driven retelling
- Mood modulation (gebruikt Resonance mood data)
- Output validation

---

## Test Strategie Overzicht

### Resonance Tests:
```
tests/workers/resonance/
├── test_resonance_units.py          # 30-40 tests
│   ├── test_decay_weight()
│   ├── test_activation_calculation()
│   ├── test_diversity_selection()
│   ├── test_filtering()
│   └── ...
├── test_resonance_integration.py    # 10-15 tests
│   ├── test_kafka_flow()
│   ├── test_qdrant_integration()
│   ├── test_mood_boost()
│   └── ...
└── test_resonance_e2e.py            # 1-2 tests
    └── test_full_lifecycle()
```

### Reteller Tests (later):
```
tests/workers/reteller/
├── test_reteller_units.py           # 20-30 tests
│   ├── test_motif_extraction()
│   ├── test_forgetting_simulation()
│   ├── test_prompt_building()
│   └── ...
├── test_reteller_integration.py     # 5-10 tests
│   ├── test_llm_fallback()
│   ├── test_character_integration()
│   └── ...
└── test_reteller_e2e.py             # 1-2 tests
    └── test_full_narrative_flow()
```

---

## Beslissing Checklist

Voor je begint, check:

- [ ] **Resonance plan gereviewd** ✓
- [ ] **Reteller plan gereviewd** ✓
- [ ] **Team consensus** (Lonn, Coen)
- [ ] **Test infrastructure setup** (pytest, fixtures)
- [ ] **CI/CD pipeline** (optioneel, maar handig)
- [ ] **Documentation** (test strategy, enhancement plans)

---

**Document Version**: 1.0  
**Date**: 2025-11-21  
**Author**: Planning session met crocodeux

