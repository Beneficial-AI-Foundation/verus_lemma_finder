# Multi-stage build for minimal image size
FROM python:3.12-slim as builder

WORKDIR /app

# Install uv (fast Python package installer)
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml Readme.md ./
COPY src/ ./src/

# Install dependencies
RUN uv pip install --system -e ".[demo]"

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY demo/ ./demo/
COPY data/ ./data/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the application (Fly.io will override PORT if needed)
CMD uvicorn demo.server:app --host 0.0.0.0 --port ${PORT:-8000}

