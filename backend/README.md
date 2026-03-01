## Fin-Eye Backend (FastAPI)

This directory contains the Python backend for Fin-Eye, implemented with **FastAPI** as described in `prdv3-2.md`.

### Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI
- **ASGI server**: Uvicorn

### Current status

- Minimal FastAPI app with:
  - `GET /health` endpoint returning `{"status": "ok"}` for basic liveness checks.
- Further endpoints, data pipelines, and ML logic will be added to satisfy `MVP-DATA-01` and related stories.

### Running locally (once dependencies are installed)

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/health` to verify the service is running.

