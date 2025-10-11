# The Ebbinghaus Forgetting Curve in Virtual Human Memory

## What is the Ebbinghaus Forgetting Curve?

The **Ebbinghaus Forgetting Curve** is one of the foundational discoveries in cognitive psychology, first documented by German psychologist Hermann Ebbinghaus in 1885. Through meticulous self-experimentation, Ebbinghaus discovered that human memory doesn't fade linearly over time—instead, it follows an **exponential decay pattern**.

### The Original Discovery

Ebbinghaus memorized lists of nonsense syllables (like "WID", "ZOF", "KAL") to eliminate the effect of prior knowledge or meaning. He then tested himself at various intervals to measure retention. His groundbreaking finding:

**Memory retention decreases exponentially with time**, following the mathematical formula:

```
R = e^(-t/S)
```

Where:

- **R** = Retention (percentage of information remembered)
- **t** = Time elapsed since learning
- **e** = Euler's number (~2.71828)
- **S** = Stability of memory (how "strong" the memory is)

### Key Insights from Ebbinghaus

1. **Rapid initial forgetting**: Most forgetting happens shortly after learning (within hours/days)
2. **Leveling off**: The rate of forgetting slows over time—what remains becomes more stable
3. **Individual variation**: Different types of memories have different decay rates
4. **Emotional significance matters**: Emotionally charged or meaningful information decays more slowly

## Why This Matters for Virtual Humans

Traditional AI systems treat all retrieved information equally, regardless of when it was learned. This creates an unnatural, "photographic memory" effect where decade-old conversations are recalled with the same vividness as yesterday's interactions.

**Human-like conversation requires forgetting.** People don't perfectly recall everything—memories become:

- **Fuzzier over time** (details fade)
- **Less accessible** (harder to spontaneously recall)
- **More gist-based** (essence remains, specifics blur)

Our Virtual Human memory system implements the Ebbinghaus curve to create **psychologically realistic forgetting**, making interactions feel more natural and human.

## Implementation in Our System

### Mathematical Model

We implement exponential decay in the **Resonance Worker**, which calculates a decay weight for each memory during recall:

```python
def decay_weight(stored_at_iso: str, now: datetime) -> float:
    """
    Calculate how much a memory has faded based on the Ebbinghaus forgetting curve.

    Args:
        stored_at_iso: ISO timestamp when memory was created
        now: Current timestamp

    Returns:
        Float between 0 and 1, where 1 = perfectly fresh, 0 = completely forgotten
    """
    stored = datetime.fromisoformat(stored_at_iso)
    age_days = (now - stored).days

    # Exponential decay with lambda (λ) = 0.002
    # This means ~18% decay after 100 days, ~63% after 500 days
    return math.exp(-LAM * max(age_days, 0))
```

### Parameters

Our implementation uses:

```python
LAM = 0.002  # Lambda (λ): time decay constant per day
```

**What does λ = 0.002 mean?**

- After **1 day**: Memory retains ~99.8% strength (almost perfect recall)
- After **7 days**: Memory retains ~98.6% strength (still very strong)
- After **30 days**: Memory retains ~94.2% strength (slight fading)
- After **100 days**: Memory retains ~81.9% strength (noticeable fading)
- After **365 days**: Memory retains ~48.5% strength (significant fading)
- After **1000 days**: Memory retains ~13.5% strength (distant memory)

This creates a **realistic memory lifecycle** where:

- Recent events (hours/days) are recalled vividly
- Medium-term events (weeks/months) are strong but slightly faded
- Long-term events (years) require strong semantic matches to surface

### Activation Strength Calculation

Decay doesn't work alone. We combine it with **semantic similarity** and **emotional salience** to compute an **activation score**:

```python
activation = similarity_score × decay_weight × salience
```

Where:

- **similarity_score** (0-1): How semantically related is this memory to the query?
- **decay_weight** (0-1): How much has this memory faded over time?
- **salience** (0-∞, typically 0.5-2.0): How emotionally significant was this event?

**Example scenario:**

```
Memory: "We demoed our Virtual Human at Fontys; lively Q&A about ethics"
Stored: 280 days ago
Salience: 1.0 (normal event)

Query: "Tell me about the Virtual Human demo"

Calculation:
- Semantic similarity: 0.89 (high match)
- Decay weight: exp(-0.002 × 280) = 0.573 (moderate fading)
- Salience: 1.0 (normal)

Activation = 0.89 × 0.573 × 1.0 = 0.510
```

This memory might surface if no fresher, more relevant memories exist. But a 1-day-old memory with similarity 0.70 would score higher (0.70 × 0.998 × 1.0 = 0.698).

## Tunability: Adjusting the Decay Rate

Different types of memories decay at different rates. Our system can be tuned by adjusting `LAM`:

| Lambda (λ) | Decay Rate  | Use Case                                    |
| ---------- | ----------- | ------------------------------------------- |
| **0.001**  | Slow        | Long-term memories, significant life events |
| **0.002**  | **Default** | Normal conversational memories              |
| **0.005**  | Fast        | Ephemeral information (weather, small talk) |
| **0.01**   | Very fast   | Ultra-short-term context (last sentence)    |

### Future: Per-Memory Decay Rates

The current implementation uses a global `LAM`. A more sophisticated system could assign different decay rates based on memory type:

```python
# Hypothetical future implementation
DECAY_RATES = {
    "episodic": 0.002,      # Personal experiences
    "semantic": 0.0005,     # Facts, knowledge
    "procedural": 0.0001,   # Skills, habits
    "emotional": 0.001,     # Emotionally charged events
}
```

## Psychological Realism Features

### 1. Recency Bias

The exponential curve naturally creates **recency bias**—a well-documented cognitive phenomenon where recent events are more easily recalled:

```
Yesterday's meeting > Last month's similar meeting > Last year's similar meeting
```

Even if all three meetings discussed the same topic, the recent one dominates recall unless the older ones had exceptional salience.

### 2. Detail Degradation

Our **Reteller Worker** uses memory age to adjust narrative detail:

```python
# For memories older than ~9 months
if "months" in perceived_age or "years" in perceived_age:
    # Remove specific times: "14:30" → "around then"
    text = re.sub(r"\b\d{1,2}[:h][0-5]\d\b", "around then", text)
    # Remove specific numbers: "12 colleagues" → "a handful"
    text = re.sub(r"\b\d{1,2}\b", "a handful", text)
    # Remove specific locations: "R10" → "a room"
    text = re.sub(r"(R\d+|room\s*\w+)", "a room", text, flags=re.I)
```

**Result**:

- Recent memory: "We demoed in R10 at 14:30 to 12 Fontys colleagues"
- Old memory: "We demoed in a room around then to a handful of colleagues"

This mirrors how human memories lose specificity over time while retaining the emotional gist.

### 3. Gist Extraction

As memories age, people remember the **essence** more than the **details**. Our Phi4/Qwen3 retelling naturally produces this effect:

**Fresh memory (1 day ago):**

> "Yesterday, we demonstrated our Virtual Human to a dozen Fontys colleagues in R10. The session included a lively Q&A focused on memory and ethics, with particularly engaging questions about data retention and transparency."

**Aged memory (9 months ago):**

> "We demoed the Virtual Human to Fontys colleagues some months back—there was a good discussion around ethics and memory, though the specifics are a bit hazy now."

## Comparison to Other Memory Models

### Traditional RAG (Retrieval-Augmented Generation)

```
Time-agnostic retrieval → All memories treated equally
Problem: "Photographic memory" effect, unnatural conversations
```

### Simple Recency Filtering

```
Only retrieve memories from last N days
Problem: Binary cutoff, old significant events are lost entirely
```

### Our Ebbinghaus-Based Approach

```
Exponential decay × similarity × salience → Activation score
Benefit: Gradual, natural fading while preserving important old memories
```

**Example**: A traumatic or highly salient event from years ago (salience = 2.0) can still surface if relevant, while mundane recent events might not.

## Validation and Tuning

### How to Test If Decay Feels Right

1. **Create memories at different time points** (use `tools/validation_experiments.py` with adjusted timestamps)
2. **Query for related information**
3. **Observe which memories surface and in what order**
4. **Check if the pattern feels human-like**

### Signs the Decay Rate is Wrong

**Too slow (λ too small)**:

- Old memories dominate even when recent ones are relevant
- System feels like it "can't move on" from past events

**Too fast (λ too large)**:

- Only yesterday's events are ever recalled
- System feels "forgetful" or like it has amnesia

**Just right (current λ = 0.002)**:

- Recent events are prioritized but not exclusive
- Significant old events can still surface when relevant
- Conversation feels natural—neither photographic nor amnesic

## Research Background

### Ebbinghaus's Original Work

**Title**: _Über das Gedächtnis_ (On Memory, 1885)

**Key contributions**:

- First quantitative study of memory
- Discovery of the forgetting curve
- Introduction of the "savings method" (relearning is faster than initial learning)
- Demonstrated that forgetting follows mathematical laws

### Modern Refinements

**Spaced Repetition (Piotr Woźniak, SuperMemo)**:

- Showed that reviewing material at strategic intervals can flatten the forgetting curve
- Our system could implement this: frequently recalled memories could have their `stored_at` timestamp "refreshed" (memory reconsolidation)

**Bahrick's "Permastore"**:

- Some memories reach a stable plateau and stop decaying significantly
- Future enhancement: memories recalled many times could have reduced λ

**Emotion and Memory (McGaugh)**:

- Emotionally arousing events are remembered better and longer
- Already implemented via our `salience` parameter

## Future Enhancements

### 1. Memory Reconsolidation

When a memory is recalled, it could be "refreshed":

```python
if memory.times_recalled > 3:
    # Memory is being reinforced through retrieval
    memory.stored_at = now  # Reset the clock
    memory.salience *= 1.1  # Increase importance
```

### 2. Context-Dependent Decay

Different contexts have different forgetting rates:

```python
CONTEXT_DECAY = {
    "work_projects": 0.002,    # Normal decay
    "personal_milestones": 0.001,  # Slower decay
    "weather_comments": 0.01,  # Fast decay
    "names_faces": 0.003,      # Slightly faster (realistic!)
}
```

### 3. Interference Effects

Newer similar memories could accelerate the fading of older ones:

```python
# If many similar memories exist, older ones fade faster
interference_factor = 1 + (0.1 * count_similar_memories)
adjusted_decay = LAM * interference_factor
```

### 4. Sleep and Consolidation

Biological memory research shows sleep consolidates memories. For a Virtual Human with simulated "sleep cycles":

```python
def consolidate_during_sleep():
    # Memories recalled today become more stable
    for memory in today_recalled_memories:
        memory.salience *= 1.15
        memory.decay_lambda *= 0.9  # Slower future decay
```

## References and Further Reading

1. **Ebbinghaus, H.** (1885). _Über das Gedächtnis_. English translation: _Memory: A Contribution to Experimental Psychology_.

2. **Wixted, J. T., & Ebbesen, E. B.** (1991). On the form of forgetting. _Psychological Science_, 2(6), 409-415.

3. **Murre, J. M., & Dros, J.** (2015). Replication and analysis of Ebbinghaus' forgetting curve. _PLOS ONE_, 10(7).

4. **Woźniak, P., & Gorzelańczyk, E. J.** (1994). Optimization of repetition spacing in the practice of learning. _Acta Neurobiologiae Experimentalis_, 54, 59-62.

5. **McGaugh, J. L.** (2004). The amygdala modulates the consolidation of memories of emotionally arousing experiences. _Annual Review of Neuroscience_, 27, 1-28.

## Conclusion

The Ebbinghaus forgetting curve is not just a historical curiosity—it's a **fundamental principle of human memory** that, when properly implemented, transforms AI memory systems from unrealistic "perfect recall" machines into psychologically credible conversational agents.

By combining exponential temporal decay with semantic similarity and emotional salience, our Virtual Human memory system achieves:

- ✅ **Realistic recency bias** (recent events are easier to recall)
- ✅ **Graceful degradation** (old memories fade but don't disappear)
- ✅ **Emotionally-weighted recall** (significant events persist longer)
- ✅ **Detail loss over time** (gist remains, specifics blur)

This creates conversations that feel **genuinely human**—where the AI "remembers like we do," with all the natural imperfections that make memory feel authentic.

---

**Current implementation**: `convai_narrative_memory_poc/workers/resonance/main.py`  
**Configuration**: Adjust `LAM` constant for different decay rates  
**Testing**: Use `convai_narrative_memory_poc/tools/validation_experiments.py` with varied timestamps
