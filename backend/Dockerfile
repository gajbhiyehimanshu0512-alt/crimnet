# Multi-stage build for FastAPI backend
# Stage 1: Build
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies needed for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and build wheels (layer caching)
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy wheels from builder
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install Python packages from wheels (fast, no compilation)
RUN pip install --no-cache /wheels/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Create uploads directory
RUN mkdir -p uploads && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check (Render and friends set $PORT; local Docker leaves it unset)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sh -c "python -c \"import urllib.request,os;urllib.request.urlopen('http://localhost:' + os.environ.get('PORT','8000') + '/health', timeout=5)\""

# Render assigns a random $PORT and expects us to bind to it — hardcoding 8000
# makes the health check fail and the service never go live. One worker by
# default: four workers each loading spaCy/ChromaDB exhaust a free instance.
CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}"
