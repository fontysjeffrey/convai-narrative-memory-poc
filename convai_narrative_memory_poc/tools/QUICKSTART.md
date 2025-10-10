# Chatbot Demo - Quick Start

## 🚀 Fastest Way to Run

```bash
# From the repository root
cd convai_narrative_memory_poc

# Start the full stack (one-time setup)
docker compose up -d kafka qdrant indexer resonance reteller

# Wait ~10 seconds for services to initialize, then run the chatbot
docker compose run --rm chatbot
```

## 🎯 What You'll See

```
╔════════════════════════════════════════════════════════════╗
║     🧠 Memory-Enhanced Chatbot - Kafka Stack Demo 🧠      ║
╚════════════════════════════════════════════════════════════╝

Connected to: Kafka @ kafka:9092
Session ID: a3f8e2c1

Type /help for commands or just chat naturally!

You: I'm researching narrative memory at Fontys
📝 Stored anchor: 4f3a2b1c... | salience: 0.9

Bot: Hello! I'm a memory-enhanced chatbot...
📝 Stored anchor: 7e9d3c2a... | salience: 0.7
```

## 🕐 Demo the Forgetting Curve

```
You: My research focuses on time-based decay
📝 Stored anchor: 2b8f4d9e... | salience: 0.9
🔍 Recalled 2 memories | avg activation: 0.89
💭 Beat 1: "researching narrative memory at Fontys" (just now) | act: 0.91

You: /advance_time 90d
⏰ Time advanced by 90 days (3 months)

You: What was I researching?
🔍 Recalled 2 memories | avg activation: 0.64
💭 Beat 1: "narrative memory at Fontys" (3 months ago) | act: 0.67
💭 Beat 2: "time-based decay" (3 months ago) | act: 0.61

Bot: About 3 months ago, you mentioned researching narrative
     memory at Fontys, focusing on time-based decay...
```

## 📋 Key Commands

- `/advance_time 30d` - Jump forward 30 days
- `/advance_time 6m` - Jump forward 6 months
- `/advance_time 1y` - Jump forward 1 year
- `/reset_time` - Back to present
- `/help` - Full command list
- `/exit` - Quit

## 🎓 For Research Presentations

This demo shows:

1. **Real Kafka stack** - Not a simulation, actual distributed messaging
2. **Semantic search** - Finds related memories, not exact matches
3. **Time-based decay** - Exponential forgetting: `activation = similarity × e^(-λ × age) × salience`
4. **Transparent operations** - See what's happening under the hood
5. **Realistic memory** - Recent details are crisp, old memories fade

## 🛠️ Troubleshooting

**Can't connect to Kafka?**

```bash
docker compose ps  # Check services are running
docker compose logs kafka  # Check for errors
```

**No memories retrieved?**

```bash
docker compose ps indexer resonance  # Ensure workers are running
docker compose logs indexer  # Check indexing is happening
```

**Services not starting?**

```bash
docker compose down  # Clean shutdown
docker compose up -d kafka qdrant  # Start infrastructure first
sleep 10  # Wait for Kafka to be ready
docker compose up -d indexer resonance reteller  # Then workers
```

## 🧹 Cleanup

```bash
# Stop all services
docker compose down

# Remove stored data (fresh start)
docker compose down -v
```

## 📚 More Info

- Full demo guide: [CHATBOT_DEMO.md](CHATBOT_DEMO.md)
- Architecture: [../../research/architecture.md](../../research/architecture.md)
- Research proposal: [../../research/research_proposal.md](../../research/research_proposal.md)

---

**Happy researching! 🧠✨**
