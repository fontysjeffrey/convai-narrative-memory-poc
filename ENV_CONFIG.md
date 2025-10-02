# Environment Configuration Guide

## Embedding Model Configuration

Choose which embedding model to use for semantic search in your `.env` file or export as environment variables:

### Available Options

```bash
# Option 1: Deterministic (default) - Fast, no dependencies, good for testing
EMBEDDING_MODEL=deterministic

# Option 2: Nomic Embed Text - Excellent for semantic search, 274MB, fast
EMBEDDING_MODEL=nomic-embed-text

# Option 3: MXBai Embed Large - High quality retrieval, 669MB
EMBEDDING_MODEL=mxbai-embed-large

# Option 4: BGE-M3 - BAAI General Embedding v3, multilingual, 1.2GB, state-of-the-art
EMBEDDING_MODEL=bge-m3
```

**Note**: For non-deterministic models, Ollama must be running with the model already pulled.

## LLM Configuration for Narrative Retelling

### Ollama Configuration

```bash
# Ollama base URL (default works for local Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# Choose your Ollama model for narrative generation
# Based on your available models:
OLLAMA_MODEL=llama3           # 4.7GB, fast, good quality (default)
# OLLAMA_MODEL=qwen3          # 5.2GB, excellent reasoning
# OLLAMA_MODEL=gemma3:12b     # 8.1GB, high quality output
# OLLAMA_MODEL=mistral        # 4.1GB, balanced performance
# OLLAMA_MODEL=phi4           # 9.1GB, smart and efficient
# OLLAMA_MODEL=qwen3:30b      # 18GB, most capable but slower
```

### OpenAI Configuration (Alternative)

```bash
# If set, OpenAI will be tried first, then Ollama, then stub fallback
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini      # or gpt-4o, gpt-3.5-turbo
```

## Quick Start Examples

### Example 1: Use BGE-M3 for embeddings + Qwen3 for retelling

```bash
export EMBEDDING_MODEL=bge-m3
export OLLAMA_MODEL=qwen3
docker compose -f convai_narrative_memory_poc/docker-compose.yml up -d
```

### Example 2: Use Nomic embeddings + Gemma for retelling

```bash
export EMBEDDING_MODEL=nomic-embed-text
export OLLAMA_MODEL=gemma3:12b
docker compose -f convai_narrative_memory_poc/docker-compose.yml up -d
```

### Example 3: Fast testing mode (deterministic embeddings + stub)

```bash
# No env vars needed - this is the default
docker compose -f convai_narrative_memory_poc/docker-compose.yml up -d
```

### Example 4: Production with OpenAI

```bash
export EMBEDDING_MODEL=bge-m3
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4o
docker compose -f convai_narrative_memory_poc/docker-compose.yml up -d
```

## Testing Your Configuration

After starting the services, run:

```bash
# Check that workers are using the correct models
docker compose -f convai_narrative_memory_poc/docker-compose.yml logs indexer | head -20
docker compose -f convai_narrative_memory_poc/docker-compose.yml logs reteller | head -20

# Run the test
docker compose -f convai_narrative_memory_poc/docker-compose.yml run --rm tools

# Check the retelling output
docker compose -f convai_narrative_memory_poc/docker-compose.yml logs reteller --tail=30
```

## Troubleshooting

### "Ollama embedding failed"
- Ensure Ollama is running: `ollama list`
- Ensure the embedding model is pulled: `ollama pull bge-m3`
- Check Ollama is accessible: `curl http://localhost:11434/api/tags`

### "Reteller using stub instead of LLM"
- Check `OLLAMA_BASE_URL` is correct
- Ensure `OLLAMA_MODEL` is pulled: `ollama pull llama3`
- Check reteller logs for errors: `docker compose logs reteller`

### Docker can't reach Ollama
- Use `http://host.docker.internal:11434` instead of `localhost:11434`
- This is already the default in `docker-compose.yml`
