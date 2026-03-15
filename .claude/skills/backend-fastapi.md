# Skill: Backend FastAPI Patterns (fin-eye specific)
# When to load: Before writing or reviewing any backend service, API endpoint,
#               database query, or async code in fin-eye.

## Core Patterns

### Service Layer vs CRUD Layer
fin-eye enforces a strict separation:
- `app/crud/` — raw DB queries only. No business logic. Returns ORM models.
- `app/services/` — business logic. Calls CRUD, calls external APIs, computes scores.
- `app/api/` — thin HTTP layer. Validates input (Pydantic), calls services, returns DTOs.

**Never put business logic in a router. Never put DB queries in a service directly — use CRUD.**

### Async Sessions
All DB operations use `AsyncSession` from SQLAlchemy 2.0 style:
```python
# Correct
result = await db.execute(select(Model).where(Model.field == value))
rows = result.scalars().all()

# Wrong — do not use Session.query() in async code
rows = db.query(Model).filter(...).all()  # blocks the event loop
```

### Background / CPU-Bound Work
ML inference (`joblib`, `sklearn`, `xgboost`) is CPU-bound and blocks the event loop.
Always wrap in `loop.run_in_executor`:
```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, compute_technical_consensus, symbol)
```
See `gas_precompute.py: _compute_technical_score()` for the established pattern.

### Error Handling in Services
Services should raise ValueError for domain errors (bad input, insufficient data).
Routers catch these and return appropriate HTTP status codes.
Analytics events must NEVER fail a business flow — always wrap in try/except.

### Cache Pattern
Always use the three-tier read in `gas_precompute.py: get_snapshot_cached()` as the template:
1. Check Redis first
2. Fall back to DB
3. Fall back to live compute

Never call live compute in a hot path (request handler) without the cache check first.

### Alembic Migrations
- One migration per logical change
- Always provide a `downgrade()` function
- Adding a NOT NULL column to an existing table requires a default value in the migration
- Test migrations on a copy of the DB before merging

## Environment Config
All config comes from `app/config.py` via `get_settings()` (uses pydantic-settings).
Never hardcode URLs, credentials, or feature flags. Add to `.env.example` when adding new settings.
