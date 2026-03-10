# ─────────────────────────────────────────────────────────────────────────────
# Fin-Eye Backend — Production Dockerfile
# BUG-002 FIX: Enables containerised deployment to any cloud platform.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2, scikit-learn, XGBoost
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create model artifact directories (will be overridden by S3 download in prod)
RUN mkdir -p data/models model_store/artifacts

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Use gunicorn with uvicorn workers for production
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "app.main:app"]
