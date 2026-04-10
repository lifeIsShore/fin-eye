# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Install all build deps and Python packages here, not in the final image.
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Lean final image — no compilers, no build tools, no secrets.
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps only (libpq for asyncpg/psycopg2, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Non-root user — never run production containers as root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (respects .dockerignore — no .env, no logs, no models)
COPY . .

# Create artifact dirs; they will be overridden by a mounted volume or S3 sync in prod
RUN mkdir -p data/models model_store/artifacts && \
    chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Gunicorn + UvicornWorker: 4 workers, 120s timeout for ML-heavy endpoints
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "app.main:app"]
