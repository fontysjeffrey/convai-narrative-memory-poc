# Memory-Enhanced Chatbot Demo

A simple interactive chatbot that demonstrates the Kafka-based narrative memory system in action. Perfect for showing researchers how memories are stored, retrieved, and decay over time.

## Quick Start

### Option 1: Run with Docker Stack (Recommended)

1. **Start the full stack** (if not already running):

   ```bash
   cd convai_narrative_memory_poc
   docker compose up -d kafka qdrant indexer resonance reteller
   ```

2. **Run the chatbot**:
   ```bash
   docker compose run --rm chatbot
   ```

### Option 2: Run Locally

1. **Ensure the stack is running** (Kafka + Qdrant + workers)

2. **Run the chatbot directly**:
   ```bash
   python convai_narrative_memory_poc/tools/chatbot.py
   ```

## What It Demonstrates

### 🧠 Real-Time Memory Formation

Every conversation turn is automatically stored as a semantic "anchor" in the memory system:

- User messages stored with high salience (0.9)
- Bot responses stored with lower salience (0.7)
- Each anchor gets a unique ID and timestamp

### 🔍 Memory Retrieval with Context

When you ask questions, the bot:

- Searches for semantically similar memories in Qdrant
- Applies time-based decay to older memories
- Shows activation scores and perceived ages
- Uses the Reteller to generate coherent narratives

### ⏰ Time-Based Forgetting

The killer feature for research demos:

- Advance time artificially (days, months, years)
- See memories fade with realistic decay curves
- Compare fresh vs. aged memory recall

### 📊 Transparent Operations

See what's happening under the hood:

- 📝 Memory storage events
- 🔍 Recall operations with counts
- 💭 Individual memory beats with activation scores
- ⏰ Time manipulation effects

## Example Session

```
You: Hello! I'm working on narrative memory research at Fontys.
[📝 Stored anchor: 4f3a2b1c... | salience: 0.9]
Bot: Hello! I'm a memory-enhanced chatbot...
[📝 Stored anchor: 7e9d3c2a... | salience: 0.7]

You: We're focusing on time-based decay and forgetting curves.
[📝 Stored anchor: 2b8f4d9e... | salience: 0.9]
[🔍 Recalled 2 memories | avg activation: 0.89]
[💭 Beat 1: "working on narrative memory research..." (just now) | act: 0.91]
[💭 Beat 2: "memory-enhanced chatbot" (just now) | act: 0.87]
Bot: I remember our conversation. Just now, you mentioned working on
     narrative memory research at Fontys...

You: /advance_time 90d
[⏰ Time advanced by 90 days (3 months)]

You: What was I researching?
[🔍 Recalled 2 memories | avg activation: 0.64]
[💭 Beat 1: "narrative memory research at Fontys" (3 months ago) | act: 0.67]
[💭 Beat 2: "time-based decay and forgetting" (3 months ago) | act: 0.61]
Bot: About 3 months ago, you mentioned working on narrative memory
     research at Fontys, with a focus on time-based decay and
     forgetting curves.

You: /advance_time 9m
[⏰ Time advanced by 270 days (9 months)]

You: What do you remember about me?
[🔍 Recalled 2 memories | avg activation: 0.31]
[💭 Beat 1: "narrative memory research" (about a year ago) | act: 0.33]
[💭 Beat 2: "Fontys" (about a year ago) | act: 0.29]
Bot: If I recall correctly, about a year ago you mentioned something
     about research at Fontys. The details are a bit fuzzy now...
```

## Commands

### Chat Commands

Just type normally! Your messages are automatically stored as memories.

### Time Manipulation

- `/advance_time 30d` - Advance by 30 days
- `/advance_time 6m` - Advance by 6 months
- `/advance_time 1y` - Advance by 1 year
- `/reset_time` - Reset to present

### Utility

- `/help` - Show all commands
- `/clear` - Clear the screen
- `/exit` or `/quit` - Exit chatbot

## For Research Presentations

This demo is perfect for:

1. **Live demonstrations** - Show memory formation and recall in real-time
2. **Decay curve visualization** - Advance time and show activation drop-off
3. **Architecture walkthroughs** - Transparent logging shows Kafka topics flowing
4. **Parameter tuning** - Researchers can see salience and decay effects

## Architecture Highlights

### What's Happening Behind the Scenes:

```
User Input → [Kafka: anchors-write] → Indexer → Qdrant
                                           ↓
User Query → [Kafka: recall-request] → Resonance → [Kafka: recall-response]
                                           ↓
                                       Reteller → [Kafka: retell.response]
                                           ↓
                                    Chatbot displays result
```

### Key Components Used:

- **Kafka Topics**: `anchors-write`, `recall-request`, `recall-response`, `retell-response`
- **Indexer**: Embeds text and stores in Qdrant
- **Resonance**: Applies decay formula: `activation = similarity × exp(-λ × age) × salience`
- **Reteller**: Generates natural language narratives from memory beats

## Configuration

The chatbot respects your stack's configuration:

```bash
# Kafka connection
export KAFKA_BOOTSTRAP=localhost:9092

# For Docker, defaults are fine
```

## Troubleshooting

**"Connection refused" errors**:

- Ensure Kafka is running: `docker compose ps kafka`
- Check logs: `docker compose logs kafka`

**No memories recalled**:

- Ensure indexer is running: `docker compose ps indexer`
- Ensure resonance is running: `docker compose ps resonance`
- Wait a few seconds after storing for indexing to complete

**No retelling generated**:

- Check reteller is running: `docker compose ps reteller`
- The chatbot will show beats even without retelling

## Tips for Demos

1. **Start with fresh conversations** - Build up context naturally
2. **Use salience strategically** - Important facts stored with high salience last longer
3. **Advance time gradually** - Show decay at 1 day, 1 week, 1 month, 1 year intervals
4. **Ask broad then specific** - Show how semantic search finds relevant memories
5. **Show the logs** - The transparent operations are the real magic!

## Next Steps

Want to extend this demo?

- Add `/inspect` command to query Qdrant directly
- Visualize activation scores over time with matplotlib
- Add memory consolidation (merge similar memories)
- Implement memory importance boosting (recently accessed memories get stronger)
- Create a web UI with real-time Kafka event visualization

Happy researching! 🧠✨
