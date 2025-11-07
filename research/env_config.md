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

**Note**: For non-deterministic models, Ollama must be running with the model already pulled. Ollama runs as a Docker service in `docker-compose.yml`.

## LLM Configuration for Narrative Retelling

### Ollama Configuration

Ollama runs as a Docker service. The default configuration connects to it via the internal Docker network.

```bash
# Ollama base URL (default connects to Docker service)
# No need to set this unless you want to override the default
OLLAMA_BASE_URL=http://ollama:11434

# Choose your Ollama model for narrative generation
# Based on your available models:
OLLAMA_MODEL=llama3           # 4.7GB, fast, good quality (default)
# OLLAMA_MODEL=qwen3          # 5.2GB, excellent reasoning
# OLLAMA_MODEL=gemma3:12b     # 8.1GB, high quality output
# OLLAMA_MODEL=mistral        # 4.1GB, balanced performance
# OLLAMA_MODEL=phi4           # 9.1GB, smart and efficient
# OLLAMA_MODEL=qwen3:30b      # 18GB, most capable but slower
```

**Note**: After starting the Docker services, you'll need to pull the models inside the Ollama container:
```bash
# Pull embedding model (e.g., bge-m3)
docker compose -f convai_narrative_memory_poc/docker-compose.yml exec ollama ollama pull bge-m3

# Pull LLM model (e.g., llama3)
docker compose -f convai_narrative_memory_poc/docker-compose.yml exec ollama ollama pull llama3
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

- Ensure Ollama container is running: `docker compose -f convai_narrative_memory_poc/docker-compose.yml ps ollama`
- Ensure the embedding model is pulled in the container: `docker compose -f convai_narrative_memory_poc/docker-compose.yml exec ollama ollama pull bge-m3`
- Check Ollama is accessible: `docker compose -f convai_narrative_memory_poc/docker-compose.yml exec ollama ollama list`
- Check Ollama logs: `docker compose -f convai_narrative_memory_poc/docker-compose.yml logs ollama`

### "Reteller using stub instead of LLM"

- Check `OLLAMA_BASE_URL` is correct (should be `http://ollama:11434` for Docker)
- Ensure `OLLAMA_MODEL` is pulled in the container: `docker compose -f convai_narrative_memory_poc/docker-compose.yml exec ollama ollama pull llama3`
- Check reteller logs for errors: `docker compose -f convai_narrative_memory_poc/docker-compose.yml logs reteller`
- Check Ollama logs: `docker compose -f convai_narrative_memory_poc/docker-compose.yml logs ollama`
