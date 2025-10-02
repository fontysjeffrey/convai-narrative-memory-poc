FROM python:3.12-slim

# Install uv and set python path
ENV PYTHONPATH=/app
RUN pip install uv

# Create a virtual environment
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files and install
COPY pyproject.toml uv.lock ./
RUN uv pip sync --no-cache pyproject.toml

# Copy the application code
COPY ./convai_narrative_memory_poc ./convai_narrative_memory_poc

# Set the command
CMD ["python", "-m", "convai_narrative_memory_poc.workers.indexer.main"]
