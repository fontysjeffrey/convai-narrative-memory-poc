# Reteller Worker Enhancement Plan

## Huidige Status Analyse

### Wat de Reteller nu doet:

1. **Input**: Consumeert `recall-response` topic met beats (anchors + perceived_age + activation)
2. **Processing**:
   - Extracteert motifs (terugkerende keywords/themes)
   - Sorteert beats temporally (recent → oud)
   - Past "forgetting" toe op tekst (details vervagen bij lage activation)
   - Bouwt narrative guidance prompt voor LLM
3. **Output**: Publiceert `retell-response` met geïntegreerde narrative
4. **LLM Modes**: OpenAI → Portkey → Ollama → Stub (fallback)

### Huidige Features:

✅ **Temporal ordering**: Beats gesorteerd op perceived age  
✅ **Forgetting simulation**: Tekst details vervagen bij lage activation  
✅ **Motif extraction**: Herkent terugkerende thema's  
✅ **Multi-LLM support**: Meerdere backends met fallback  
✅ **Stub mode**: Werkt zonder LLM (voor testing)  
✅ **Confidence hedging**: "I think", "I remember" bij onzekere memories

### Wat ontbreekt (uit research proposal):

❌ **Character-driven retelling**: Persoonlijkheid beïnvloedt hoe verhalen worden verteld  
❌ **Mood modulation**: Emotionele staat beïnvloedt recall  
❌ **Emotional tagging**: Detectie en gebruik van emotie in anchors  
❌ **Multi-agent context**: "I remember" vs "I heard from X"  
❌ **Structured output validation**: Geen garantie dat output voldoet aan requirements

---

## Enhancement Doelstellingen

### 1. Character-Driven Retelling (Priority: HIGH)

**Wat het moet doen:**
- Reteller ontvangt character profile (personality traits, mood, emotional state)
- Zelfde anchor wordt anders verteld afhankelijk van character:
  - Optimistic character: benadrukt positieve aspecten
  - Anxious character: herinnert zich risico's/bedreigingen
  - Analytical character: meer details, minder emotie
  - Empathetic character: meer focus op anderen' gevoelens

**Voorbeeld:**
```
Anchor: "System outage affecting 50+ users"

Optimistic retelling: "We had a system issue that we quickly resolved, and it taught us valuable lessons about resilience."

Anxious retelling: "There was a critical system failure that affected many users—it was stressful, but we managed to fix it."

Analytical retelling: "A system outage occurred affecting 50+ users. Root cause: database connection pool exhaustion. Resolution time: 2.3 hours."
```

### 2. Mood Modulation (Priority: MEDIUM)

**Wat het moet doen:**
- Huidige mood/emotional state beïnvloedt welke memories worden benadrukt
- Angry mood → meer negatieve memories
- Happy mood → meer positieve memories
- Neutral mood → balanced recall

**Implementatie:**
- Mood wordt doorgegeven in recall request (of via separate topic)
- Reteller past prompt aan met mood context
- LLM genereert retelling die mood reflecteert

### 3. Emotional Anchors (Priority: MEDIUM)

**Wat het moet doen:**
- Anchors kunnen emotionele metadata hebben (valence, arousal, dominance)
- Reteller gebruikt deze om retelling te sturen:
  - Negative memories: meer voorzichtig, defensief
  - High-arousal: meer levendige details
  - Low-dominance: passieve voice ("It happened to me")

**Data structuur:**
```python
{
    "anchor_id": "...",
    "text": "...",
    "emotion": {
        "valence": -0.8,  # Negative
        "arousal": 0.9,    # High intensity
        "dominance": 0.3   # Felt out of control
    }
}
```

### 4. Output Validation & Quality Control (Priority: LOW)

**Wat het moet doen:**
- Valideer dat retelling voldoet aan requirements:
  - Lengte (≤85 words)
  - Geen bullet points
  - Eerste persoon, verleden tijd
  - Geïntegreerd verhaal (niet alleen lijst)
- Fallback naar stub mode als LLM output niet voldoet

---

## Implementatie Volgorde

### Fase 1: Test Infrastructure (Week 1)

**Waarom eerst tests?**
- Reteller heeft complexe logica (motif extraction, forgetting, prompt building)
- Veel edge cases (lege beats, verschillende activation scores, etc.)
- Tests maken refactoring veiliger
- Tests documenteren verwacht gedrag

**Wat we maken:**

1. **Unit Tests** (`tests/workers/reteller/test_reteller_units.py`):
   - `test_extract_motifs()` - verschillende beat configuraties
   - `test_order_beats_temporally()` - sorting logic
   - `test_apply_forgetting_to_text()` - verschillende activation levels
   - `test_build_narrative_guidance()` - prompt structure
   - `test_narrativize_for_stub()` - stub mode output

2. **Integration Tests** (`tests/workers/reteller/test_reteller_integration.py`):
   - Mock Kafka consumer/producer
   - Test volledige flow: beats → retelling
   - Test verschillende LLM modes (OpenAI, Ollama, stub)
   - Test error handling (LLM fails → stub fallback)

3. **Test Data Fixtures** (`tests/fixtures/reteller_beats.json`):
   - Voorbeeld beats met verschillende configuraties
   - Recent vs. oude memories
   - Hoge vs. lage activation
   - Verschillende salience levels

**Test Locatie:**
```
convai_narrative_memory_poc/
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── reteller_beats.json
│   │   └── character_profiles.json
│   └── workers/
│       ├── __init__.py
│       └── reteller/
│           ├── __init__.py
│           ├── test_reteller_units.py
│           └── test_reteller_integration.py
```

**Tools:**
- `pytest` voor test framework
- `pytest-mock` voor mocking
- `pytest-cov` voor coverage

---

### Fase 2: Character-Driven Retelling (Week 2-3)

**Stap 2.1: Data Structure Design**

```python
# Character profile structuur
{
    "character_id": "uuid",
    "traits": {
        "optimism": 0.8,      # 0.0 - 1.0
        "anxiety": 0.2,
        "analytical": 0.6,
        "empathy": 0.9
    },
    "mood": {
        "valence": 0.7,       # -1.0 (sad) to 1.0 (happy)
        "arousal": 0.5,       # 0.0 (calm) to 1.0 (excited)
        "current_state": "content"  # happy, sad, anxious, angry, neutral
    }
}
```

**Stap 2.2: Prompt Enhancement**

Huidige prompt:
```python
system_prompt = "You are a Virtual Human producing an INTEGRATED memory recap..."
```

Nieuwe prompt met character:
```python
system_prompt = f"""
You are a Virtual Human producing an INTEGRATED memory recap for yourself.

Character Profile:
- Optimism: {traits['optimism']} (high = focus on positives, low = cautious)
- Analytical: {traits['analytical']} (high = detail-oriented, low = emotional)
- Empathy: {traits['empathy']} (high = focus on others, low = self-focused)

Current Mood: {mood['current_state']} (valence: {mood['valence']})

Voice: first-person, past tense, practical, emotionally neutral.
Goal: weave one coherent arc across memories instead of listing them.
Adapt your retelling style to match your character profile and current mood.
"""
```

**Stap 2.3: Integration Points**

- Character profile komt binnen via:
  - Option 1: `recall-request` payload (character_id → lookup)
  - Option 2: Separate Kafka topic (`character-state-update`)
  - Option 3: Environment variable (voor single-character setup)

**Stap 2.4: Testing**

- Test met verschillende character profiles
- Valideer dat retellingen verschillen per character
- Test edge cases (geen character profile → default behavior)

---

### Fase 3: Mood Modulation (Week 4)

**Stap 3.1: Mood Integration**

- Mood kan komen van:
  - Recent anchors (emotionele events)
  - External source (user input, sensor data)
  - Character's internal state

**Stap 3.2: Mood-Aware Prompting**

```python
if mood['valence'] < -0.5:  # Negative mood
    prompt_addition = "Given your current mood, you may recall challenges or difficulties more vividly."
elif mood['valence'] > 0.5:  # Positive mood
    prompt_addition = "Given your current mood, you may focus on positive aspects and achievements."
```

**Stap 3.3: Memory Selection Bias**

- Resonance worker kan al mood-aware zijn (selecteert memories die mood matchen)
- Reteller versterkt dit door retelling style aan te passen

---

### Fase 4: Emotional Anchors (Week 5)

**Stap 4.1: Emotion Detection**

- Option 1: LLM-based emotion detection bij anchor creation (indexer)
- Option 2: Manual tagging
- Option 3: Rule-based (keywords → emotion)

**Stap 4.2: Emotion-Aware Retelling**

```python
emotion = anchor.get("emotion", {})
if emotion.get("valence", 0) < -0.5:
    # Negative memory: more cautious retelling
    prompt_addition = "This memory has negative emotional weight—retell it with appropriate caution."
```

---

### Fase 5: Output Validation (Week 6)

**Stap 5.1: Validation Rules**

```python
def validate_retelling(text: str) -> tuple[bool, list[str]]:
    errors = []
    
    # Check length
    word_count = len(text.split())
    if word_count > 85:
        errors.append(f"Too long: {word_count} words (max 85)")
    
    # Check for bullet points
    if re.search(r'^[\s]*[-*•]', text, re.MULTILINE):
        errors.append("Contains bullet points")
    
    # Check for first person
    if not re.search(r'\b(I|we|my|our)\b', text, re.I):
        errors.append("Not first person")
    
    # Check for past tense indicators
    past_tense_indicators = ['was', 'were', 'had', 'did', 'went', 'said']
    if not any(indicator in text.lower() for indicator in past_tense_indicators):
        errors.append("May not be past tense")
    
    return len(errors) == 0, errors
```

**Stap 5.2: Fallback Logic**

```python
text = call_llm(...)
is_valid, errors = validate_retelling(text)

if not is_valid:
    print(f"[reteller] LLM output invalid: {errors}, using stub")
    text = retell_stub(beats)
```

---

## Test Strategie

### Test Pyramid

```
        /\
       /  \      E2E Tests (1-2)
      /____\
     /      \    Integration Tests (5-10)
    /________\
   /          \  Unit Tests (20-30)
  /____________\
```

### Unit Tests (Bottom Layer)

**Focus**: Individuele functies, edge cases

```python
# test_reteller_units.py

def test_extract_motifs_empty_beats():
    """Test motif extraction with empty input"""
    assert extract_motifs([]) == {
        "per_beat_keywords": [],
        "recurrent": set(),
        "theme_guess": "continuity of work across time"
    }

def test_extract_motifs_single_beat():
    """Test motif extraction with single beat"""
    beats = [{"text": "We demoed the system to colleagues"}]
    result = extract_motifs(beats)
    assert "demoed" in result["recurrent"] or "system" in result["recurrent"]

def test_apply_forgetting_high_activation():
    """Test forgetting with high activation (should preserve details)"""
    text = "Meeting at 14:30 in R10 with 12 people"
    result = apply_forgetting_to_text(text, activation=0.9)
    assert "14:30" in result or "R10" in result

def test_apply_forgetting_low_activation():
    """Test forgetting with low activation (should remove details)"""
    text = "Meeting at 14:30 in R10 with 12 people"
    result = apply_forgetting_to_text(text, activation=0.4)
    assert "14:30" not in result
    assert "R10" not in result or "a room" in result
```

### Integration Tests (Middle Layer)

**Focus**: Component interactions, Kafka flow

```python
# test_reteller_integration.py

def test_reteller_kafka_flow(mock_kafka):
    """Test full Kafka consumer → processing → producer flow"""
    # Setup: mock Kafka consumer with test beats
    # Execute: run reteller main loop
    # Assert: verify output message structure

def test_reteller_llm_fallback():
    """Test that stub mode is used when LLM fails"""
    # Mock LLM to fail
    # Verify stub output is used

def test_reteller_character_integration():
    """Test character profile affects retelling"""
    beats = load_fixture("test_beats.json")
    character = load_fixture("optimistic_character.json")
    
    optimistic_retelling = retell_with_character(beats, character)
    pessimistic_retelling = retell_with_character(beats, pessimistic_character)
    
    assert optimistic_retelling != pessimistic_retelling
    assert "positive" in optimistic_retelling.lower() or "achievement" in optimistic_retelling.lower()
```

### E2E Tests (Top Layer)

**Focus**: Volledige system flow

```python
# test_reteller_e2e.py

def test_full_memory_lifecycle():
    """Test: anchor → recall → retell"""
    # 1. Create anchor via indexer
    # 2. Request recall via resonance
    # 3. Verify reteller produces output
    # 4. Check output quality
```

---

## File Structure

```
convai_narrative_memory_poc/
├── workers/
│   └── reteller/
│       ├── main.py                    # Huidige implementatie
│       ├── character.py               # NIEUW: Character profile handling
│       ├── emotion.py                 # NIEUW: Emotion detection/usage
│       ├── validation.py              # NIEUW: Output validation
│       └── prompts.py                 # NIEUW: Prompt templates
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── reteller_beats.json
│   │   └── character_profiles.json
│   └── workers/
│       └── reteller/
│           ├── test_reteller_units.py
│           ├── test_reteller_integration.py
│           └── test_reteller_e2e.py
└── research/
    └── reteller_enhancement_plan.md   # Dit document
```

---

## Success Criteria

### Fase 1 (Tests):
- ✅ >80% code coverage voor reteller
- ✅ Alle edge cases hebben tests
- ✅ Tests kunnen draaien zonder Docker/Kafka (mocked)

### Fase 2 (Character-Driven):
- ✅ Retellingen verschillen significant tussen characters (>30% word overlap)
- ✅ Character traits zijn zichtbaar in output (human evaluation)
- ✅ Backward compatible (geen character = default behavior)

### Fase 3 (Mood):
- ✅ Mood beïnvloedt retelling style
- ✅ Mood changes reflecteren in output

### Fase 4 (Emotion):
- ✅ Emotional anchors leiden tot passende retelling style
- ✅ Negative memories worden voorzichtiger verteld

### Fase 5 (Validation):
- ✅ >95% van LLM outputs voldoen aan requirements
- ✅ Fallback naar stub werkt betrouwbaar

---

## Risico's & Mitigatie

| Risico | Impact | Mitigatie |
|--------|--------|-----------|
| Character profiles maken retellingen te voorspelbaar | Medium | Test met diverse characters, human evaluation |
| LLM output inconsistent | High | Output validation + fallback |
| Performance degradation | Medium | Benchmark tests, caching |
| Backward compatibility broken | High | Feature flags, default values |

---

## Volgende Stappen

1. **Review dit plan** met team (Lonn, Coen)
2. **Beslissen**: Starten met tests of direct character-driven?
3. **Setup test infrastructure**: pytest, fixtures, CI/CD
4. **Begin met Fase 1**: Unit tests voor bestaande functies

---

**Document Version**: 1.0  
**Date**: 2025-11-21  
**Author**: Planning session met crocodeux

