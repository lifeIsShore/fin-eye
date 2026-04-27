# Fin-Eye — Sprint Plans 46–55
> **Created:** April 2026
> **Author:** Product + Dev planning session
> **Basis:** Full audit of todos.md · todos-v3.md · todos-v4.md · todos-v5.md · todos-v6.md · SPRINT_PROGRESS.md (Sprints 0–45 complete)
> **Legend:** BE = Backend · FE = Frontend · DB = Database/Migration · ML = Machine Learning

---

## HOW THESE SPRINTS WERE DERIVED

Every todo item across all todo files was cross-checked against SPRINT_PROGRESS.md.
Items marked ✅ or [x] in any todo file AND confirmed built in sprint progress were excluded.
Items remaining are ONLY items that have never been built.

Sprints are ordered by: (1) security/launch readiness, (2) user retention impact, (3) product completeness, (4) technical debt.

---

## ✅ Completed: Sprints 0–45 (summary)
All bulk pipeline, ML, news, external signals, social intelligence, UX polish, onboarding,
monetisation, community leaderboard, lifestyle finance, B2B tenant foundation, and all
todo-v5/v6 blockers are complete. See SPRINT_PROGRESS.md for full details.

---

## ✅ Sprint 46 — Security Hardening (Pre-Launch Blockers)
**Completed:** April 2026

### Delivered
- [x] **SEC-01** — `.gitignore` audited: `.env`, `.env.local`, `backend/.env`, `frontend/.env.local` all excluded. `.env.example` uses blank `REPLACE_ME` placeholders throughout.
- [x] **SEC-02** — Production startup assertion in `main.py`: asserts `DEBUG=False`, no `*` in `ALLOWED_ORIGINS`, non-placeholder `JWT_SECRET` when `APP_ENV=production`. Logs `⚙️ Running in {env} mode` on every start.
- [x] **SEC-03/04/05/06** — Verified active: slowapi rate limiting, JTI token blacklisting on logout/rotate, account lockout after 10 failed logins, security headers middleware.
- [x] **SEC-07** — Email verification:
  - `POST /auth/verify-email?token=` — consumes token, sets `is_verified=True`, handles expired (410) and invalid (404)
  - `POST /auth/resend-verification` — rate-limited 3/hour/IP, generates fresh 24h token, sends via Resend
  - Registration flow sends verification email automatically after signup
  - `EmailVerificationBanner.tsx` — amber banner in layout when `user.is_verified === false`, with Resend button
  - `/verify-email` page — handles token from email link, shows success/expired/error states
  - `User.is_verified` added to frontend `User` interface in `AuthProvider.tsx`
  - `get_current_active_verified_user` dependency already in `deps.py` (confirmed + dev bypass)
- [x] **SEC-08** — `model_storage.py` (NEW): R2/S3-compatible cloud storage for ML artifacts
  - `upload_model(path)` — async, runs in executor, fires after every successful training run
  - `download_model_if_missing(path)` — downloads from R2 if local artifact missing
  - `sync_models_from_r2()` — startup job that downloads all registry-listed artifacts missing locally
  - Wired into `main.py` lifespan as background task (5s delay, non-blocking)
  - Wired into `ml_pipeline.py` after `joblib.dump()` (fire-and-forget via `loop.create_task`)
  - Silently no-ops when R2 credentials not configured (local-only dev mode)

### Files Created
```

---

## Bug Fixes — April 21, 2026 (Session 7)
**Scope:** Seed pipeline, ML training pipeline, Redis, DB model fix.

### Bugs Fixed

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `app/models/showcase.py` | `FeatureInterest.user_id` FK pointed to `"user.id"` (wrong table name) and used `Integer` type instead of `UUID` | Changed to `ForeignKey("users.id")`, `UUID(as_uuid=True)`; added `UUID` import |
| 2 | `docker-compose.yml` | Redis container started without reading `.env`, so `${REDIS_PASSWORD}` resolved to fallback `changeme_set_REDIS_PASSWORD_in_env` — auth mismatch with backend | Added `env_file: - ./backend/.env` to redis service |
| 3 | `app/services/technical_training.py` | `LabelEncoder` imported inside loop body only; `multi_class="auto"` deprecated in sklearn 1.5; `max_iter=1000` caused convergence warnings | Moved `LabelEncoder` import to top-level; removed `multi_class` arg; raised `max_iter` to 2000 |
| 4 | `scripts/seed_training_data.py` | `db.add()` on `StockOHLCV` and `SentimentAggregate` crashed with `IntegrityError` on re-runs due to unique constraint violations | Replaced with `pg_insert(...).on_conflict_do_nothing()` |
| 5 | `scripts/run_technical_training.py` | `--timeframe` choices used `"1w"`/`"1m"` but `Timeframe` enum values are `"1wk"`/`"1mo"` — caused `ValueError` at parse time | Updated choices to `["1h", "4h", "1d", "1wk", "1mo", "all"]` |

### Files Modified (Session 7 — April 21, 2026)
```
backend/app/models/showcase.py                    # FeatureInterest FK: user.id → users.id, Integer → UUID
docker-compose.yml                                # redis env_file: ./backend/.env
backend/app/services/technical_training.py        # LabelEncoder top-level import; removed multi_class; max_iter=2000
backend/scripts/seed_training_data.py             # on_conflict_do_nothing for StockOHLCV + SentimentAggregate
backend/scripts/run_technical_training.py         # timeframe choices: 1w→1wk, 1m→1mo
```
backend/app/services/model_storage.py
frontend/components/EmailVerificationBanner.tsx
frontend/app/verify-email/page.tsx
```

### Files Modified
```
backend/app/api/v1/auth.py         # verify-email + resend-verification endpoints; sends token on register
backend/app/main.py                # SEC-02 production assertions + R2 startup sync
backend/app/services/ml_pipeline.py  # Upload to R2 after training
frontend/app/layout.tsx            # EmailVerificationBanner wired in
frontend/components/AuthProvider.tsx  # is_verified added to User interface
```

### Migration
```bash
alembic upgrade head  # s46_001_email_verification (already existed)
```

---

### Goal
Lock down the production environment so the app can safely receive real users.
All 8 security blockers from todos-v3.md §1 are addressed in this sprint.

### Deliverables

#### SEC-01 · API Key Rotation + Git Audit
- [ ] `BE` Rotate ALL secrets in `backend/.env`: FINNHUB_API_KEY, FRED_API_KEY, JWT_SECRET, TOTP_FERNET_KEY, RESEND_API_KEY, ANTHROPIC_API_KEY, REDIS_URL, DATABASE_URL
- [ ] `BE` Verify `backend/.env` is listed in `.gitignore` (both root and backend level)
- [ ] `BE` Run `git log --all --full-history -- '*.env'` — confirm no .env file has ever been committed
- [ ] `BE` Run `git secrets --scan-history` or `trufflehog git file://.` — scan entire repo history for leaked secrets
- [ ] `BE` Update `backend/.env.example` to have blank placeholder values for all keys (no real values)
- [ ] `FE` Same audit for `frontend/.env.local` — verify not committed, not in git history
- **Test:** `git status` shows .env as untracked; `cat .gitignore` includes `.env` and `.env.local`

#### SEC-02 · Production Config Lock
- [ ] `BE` In `backend/app/config.py`: add `APP_ENV: str = "development"` setting
- [ ] `BE` Add assertion in `main.py` startup: if `APP_ENV == "production"` then assert `DEBUG == False`, assert `ALLOWED_ORIGINS` does not contain `"*"`, assert `JWT_SECRET` is not the default placeholder
- [ ] `BE` Create `backend/.env.production.example` showing the exact values required in prod: `APP_ENV=production`, `DEBUG=False`, `ALLOWED_ORIGINS=https://fin-eye.app`, `REQUIRE_AUTH=True`
- [ ] `BE` Add a startup log line: `logger.info("Running in %s mode", settings.app_env)`
- **Test:** Starting with APP_ENV=production and DEBUG=True should raise AssertionError on startup

#### SEC-07 · Email Verification Enforcement
> Note: SEC-03 (rate limiting), SEC-04 (JTI tokens), SEC-05 (account lockout), SEC-06 (security headers) were all implemented in Bug Fix Sessions. Verify each is still working.
- [ ] `BE` Add `get_current_active_verified_user` dependency in `backend/app/api/v1/auth.py`:
  ```python
  async def get_current_active_verified_user(current_user: User = Depends(get_current_user)) -> User:
      if not current_user.is_verified:
          raise HTTPException(status_code=403, detail="Email verification required. Check your inbox.")
      return current_user
  ```
- [ ] `BE` Apply `get_current_active_verified_user` (instead of `get_current_user`) to ALL sensitive endpoints:
  - `watchlist.py` — all routes
  - `backtesting.py` — POST /backtest, POST /backtest/publish
  - `portfolios.py` — all routes
  - `allocation.py` — POST /suggest, POST /explain
  - `alerts.py` — POST, PATCH, DELETE
  - `technical.py` — POST /train/{symbol}
- [ ] `BE` In `auth.py` registration flow: send verification email via Resend on signup. Token expires 24h. Store `verification_token` + `verification_token_expires_at` on User model.
- [ ] `BE` Add `POST /auth/verify-email?token=xxx` endpoint that sets `User.is_verified = True`
- [ ] `BE` Add `POST /auth/resend-verification` endpoint (rate-limited: 3/hour) 
- [ ] `DB` Migration: add `verification_token VARCHAR(128)`, `verification_token_expires_at TIMESTAMP` to `users` table
- [ ] `FE` In `frontend/app/auth/`: show "Please verify your email" banner when `user.is_verified === false`
- [ ] `FE` Add "Resend verification email" button in the banner
- [ ] `FE` Handle 403 "Email verification required" responses gracefully — redirect to verification prompt instead of showing generic error
- **Test:** Register new user → try to add watchlist item → get 403 → verify email → retry → succeeds

#### SEC-08 · ML Model Artifacts to Cloud Storage
- [ ] `BE` Sign up for Cloudflare R2 (free tier: 10 GB/month, no egress fees) or AWS S3
- [ ] `BE` Add to `requirements.txt`: `boto3>=1.34.0` (works with R2 via S3-compatible API)
- [ ] `BE` Add to `backend/app/config.py`:
  ```python
  r2_account_id: str = ""
  r2_access_key_id: str = ""
  r2_secret_access_key: str = ""
  r2_bucket_name: str = "fin-eye-models"
  r2_endpoint_url: str = ""  # https://{account_id}.r2.cloudflarestorage.com
  ```
- [ ] `BE` Create `backend/app/services/model_storage.py`:
  ```python
  async def upload_model(local_path: Path, remote_key: str) -> str: ...
  async def download_model(remote_key: str, local_path: Path) -> None: ...
  async def model_exists_remote(remote_key: str) -> bool: ...
  ```
  - Uses `boto3.client("s3", endpoint_url=settings.r2_endpoint_url, ...)` 
  - Upload: after every successful `run_training_pipeline()` — upload .joblib file to R2
  - Download: on startup, for any model in registry but missing locally — download from R2
- [ ] `BE` Modify `model_registry.py` `save_winner()`: after saving .joblib locally, call `upload_model()`
- [ ] `BE` In `main.py` lifespan startup: after `init_db()`, call `sync_models_from_r2()` — downloads any registry-listed models missing from local `data/models/`
- [ ] `BE` Add `data/models/` to `.gitignore` (should already be there — confirm)
- **Test:** Delete local .joblib files → restart server → models re-downloaded from R2 → technical endpoints work

#### SEC-03/04/05/06 Verification
- [ ] Verify `slowapi` rate limiting is active: send 11 rapid login requests → expect 429 on 11th
- [ ] Verify JTI tokens: logout → try to use old refresh token → expect 401
- [ ] Verify account lockout: 10 failed logins → 11th attempt → expect lockout message
- [ ] Verify security headers: `curl -I https://fin-eye.app/api/v1/health` → check for CSP, X-Frame-Options, HSTS

### Migration
```bash
alembic revision --autogenerate -m "add_email_verification_fields"
alembic upgrade head
```

### Files Modified
```
backend/app/api/v1/auth.py              # get_current_active_verified_user + verify/resend endpoints
backend/app/models/user.py              # verification_token + verification_token_expires_at
backend/app/config.py                   # APP_ENV, R2 settings
backend/app/main.py                     # startup assertion + model sync
backend/app/services/model_storage.py  # NEW: R2 upload/download
backend/app/services/model_registry.py # Upload after save_winner()
backend/requirements.txt               # boto3
frontend/app/auth/                      # Verification banner + resend button
```

---

## ✅ Sprint 47 — Autonomous Trading Bot: Paper Trading Foundation
**Priority:** HIGH — most requested advanced feature, Phase 2C from todos.md
**Sources:** todos.md §2 Phase 2C · Phase 2D
**Completed:** April 2026

### Delivered
- [x] **`backend/app/models/bot.py`** — `BotConfig`, `BotPosition`, `BotAuditLog` ORM models
- [x] **`alembic/versions/s47_001_bot_tables.py`** — migration for all 3 bot tables (`bot_configs`, `bot_positions`, `bot_audit_log`)
- [x] **`models/__init__.py`** — all 3 bot models registered
- [x] **`services/bot_service.py`** — full decision engine: `evaluate_symbol()` with BUY/SELL/HOLD/SKIP/HALT logic, Kelly-based position sizing (capped 25%), stop-loss at 2×ATR, daily loss circuit breaker, `get_bot_performance()`
- [x] **`api/v1/endpoints/bot.py`** — 9 endpoints: `GET /config`, `PATCH /config`, `POST /enable`, `POST /disable`, `POST /halt`, `POST /resume`, `GET /positions`, `GET /audit-log`, `GET /performance`
- [x] **`services/scheduler.py`** — `job_bot_evaluate` registered at `:02/:17/:32/:47` UTC (2 min after GAS precompute), mon–fri 13–21h
- [x] **`main.py`** — `bot.router` registered at `/api/v1/bot`
- [x] **`frontend/app/bot/paper/page.tsx`** — full dashboard: status banner (ACTIVE/HALTED/INACTIVE + config summary), 4-stat performance grid (PnL/Win Rate/Best/Worst), open positions table with unrealised PnL, audit log with symbol filter + colour-coded action badges, settings slide-over (strategy/min-grade/position sliders/portfolio value)
- [x] **`frontend/lib/api.ts`** — `BotConfigDto`, `BotPositionDto`, `BotAuditLogEntry`, `BotPerformanceDto` + all 9 fetch/action helpers
- [x] **`frontend/components/Nav.tsx`** — “Trading Bot” added to Tools section with BETA badge

### Migration
```bash
alembic upgrade head   # s47_001_bot_tables
```

### Goal
Build the paper trading bot foundation: position tracking, decision engine, audit log, kill switch.
NO live broker connection yet — paper mode only. Validate 30 days before any live trading.

### Prerequisites
- Sprint 46 complete (security hardened before bot has any position management)
- At least 30 days of prediction data in `ml_predictions` table
- `signal_grade_history` table populated with grade changes

### Deliverables

#### DB — New Tables
- [ ] `DB` Migration `s47_001_bot_tables.py`:

  **`bot_configs` table** — one row per user, their bot settings:
  ```sql
  CREATE TABLE bot_configs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    is_enabled       BOOLEAN NOT NULL DEFAULT FALSE,
    mode             VARCHAR(10) NOT NULL DEFAULT 'paper',  -- 'paper' | 'live' (live disabled until validated)
    strategy         VARCHAR(20) NOT NULL DEFAULT 'balanced', -- 'aggressive'|'balanced'|'conservative'
    min_grade        VARCHAR(3) NOT NULL DEFAULT 'B',       -- minimum grade to trade
    max_position_pct FLOAT NOT NULL DEFAULT 0.20,           -- max % of portfolio per symbol
    max_total_pct    FLOAT NOT NULL DEFAULT 0.80,           -- max % total deployed
    max_sector_pct   FLOAT NOT NULL DEFAULT 0.40,           -- max % in one sector
    daily_loss_limit FLOAT NOT NULL DEFAULT 0.03,           -- pause if daily PnL < -3%
    portfolio_value  FLOAT NOT NULL DEFAULT 10000.0,        -- starting paper portfolio value
    halt_flag        BOOLEAN NOT NULL DEFAULT FALSE,        -- kill switch
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ
  );
  ```

  **`bot_positions` table** — what the bot currently holds (paper):
  ```sql
  CREATE TABLE bot_positions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    symbol           VARCHAR(20) NOT NULL,
    entry_price      FLOAT NOT NULL,
    entry_grade      VARCHAR(3) NOT NULL,
    entry_gas        FLOAT NOT NULL,
    size_units       FLOAT NOT NULL,        -- number of shares/units
    size_usd         FLOAT NOT NULL,        -- USD value at entry
    position_pct     FLOAT NOT NULL,        -- % of portfolio at entry
    opened_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at        TIMESTAMPTZ,
    close_price      FLOAT,
    close_reason     VARCHAR(50),           -- 'grade_drop'|'stop_loss'|'manual'|'daily_limit'
    pnl_usd          FLOAT,                 -- filled on close
    pnl_pct          FLOAT,                 -- filled on close
    is_open          BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(user_id, symbol, is_open)        -- one open position per symbol per user
  );
  ```

  **`bot_audit_log` table** — every decision, every action, immutable:
  ```sql
  CREATE TABLE bot_audit_log (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    logged_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol           VARCHAR(20),
    action           VARCHAR(20) NOT NULL,  -- 'EVALUATE'|'BUY'|'SELL'|'HOLD'|'SKIP'|'HALT'|'RESUME'
    grade            VARCHAR(3),
    gas_score        FLOAT,
    confidence       FLOAT,
    price            FLOAT,
    size_usd         FLOAT,
    reason           TEXT NOT NULL,         -- plain English explanation of why
    position_id      UUID REFERENCES bot_positions(id),
    regime           VARCHAR(30),
    macro_score      FLOAT
  );
  CREATE INDEX idx_bot_log_user_time ON bot_audit_log(user_id, logged_at DESC);
  CREATE INDEX idx_bot_log_symbol    ON bot_audit_log(symbol, logged_at DESC);
  ```

#### BE — Bot Decision Engine
- [ ] `BE` Create `backend/app/services/bot_service.py`:

  ```python
  async def evaluate_symbol(db, user_id, symbol, config: BotConfig) -> BotDecision:
      """
      Runs every 15 minutes (aligned with GAS precompute) for all bot-enabled users.
      
      Decision rules:
        1. Fetch current GAS snapshot (grade, gas_score, regime)
        2. Fetch current position for this user+symbol (if any)
        3. Apply decision matrix:
        
           GRADE A+/A + no position + grade >= config.min_grade
             → BUY (size = kelly_fraction × portfolio_value, capped at max_position_pct)
           
           GRADE D/F + open position
             → SELL (close full position, reason='grade_drop')
           
           GRADE C + open position
             → HOLD (no new entry, don't exit yet)
           
           Price dropped > 2×ATR from entry + open position
             → SELL (reason='stop_loss')
           
           Daily PnL < -daily_loss_limit × portfolio_value
             → HALT bot for 24h (set halt_flag=True)
           
           config.halt_flag == True
             → SKIP all symbols
        
        4. Log every evaluation to bot_audit_log (even SKIP/HOLD)
        5. If BUY/SELL: update bot_positions
        6. Return BotDecision with action + reason
      """
  ```

- [ ] `BE` Create `backend/app/services/bot_scheduler.py`:
  ```python
  async def job_bot_evaluate():
      """
      Runs every 15 minutes (mon-fri 13:00-21:00 UTC, aligned with market hours).
      For each user with bot enabled:
        For each symbol in user's watchlist:
          await evaluate_symbol(db, user.id, symbol, user.bot_config)
      """
  ```
  - Register in `scheduler.py`: `CronTrigger(day_of_week="mon-fri", hour="13-21", minute="0,15,30,45")`
  - Runs AFTER GAS precompute (which runs at :00/:15/:30/:45) — add 2-minute offset: minute="2,17,32,47"

#### BE — Bot API Endpoints
- [ ] `BE` Create `backend/app/api/v1/endpoints/bot.py`:

  `GET /api/v1/bot/config`
  - Returns user's bot config (creates default if none exists)
  - Response: `BotConfigResponse` with all settings + is_enabled + mode + halt_flag

  `PATCH /api/v1/bot/config`
  - Update bot settings: strategy, min_grade, max_position_pct, portfolio_value etc.
  - Validates: max_position_pct ≤ 0.25, max_total_pct ≤ 1.0, portfolio_value > 0
  - Body: `BotConfigUpdate` Pydantic model

  `POST /api/v1/bot/enable` + `POST /api/v1/bot/disable`
  - Enable: requires `is_verified=True`, requires at least 1 watchlist symbol, requires portfolio_value set
  - Disable: sets `is_enabled=False`, does NOT close open positions
  - Logs ENABLE/DISABLE action to audit log

  `POST /api/v1/bot/halt` — KILL SWITCH
  - Sets `halt_flag=True` immediately (bypasses scheduler)
  - Optionally: `{ "close_all": true }` to close all open paper positions at current price
  - Logs HALT action to audit log
  - Works even if scheduler is down (direct DB write)

  `POST /api/v1/bot/resume`
  - Clears `halt_flag=False`
  - Logs RESUME action

  `GET /api/v1/bot/positions`
  - Returns all open and recent closed positions
  - Includes current unrealised PnL (fetch current price from OHLCV or cache)

  `GET /api/v1/bot/audit-log?limit=100&symbol=AAPL`
  - Paginated audit log filtered by symbol (optional)
  - Returns last N entries newest-first

  `GET /api/v1/bot/performance`
  - Paper trading performance summary:
    - Total paper PnL (USD + %)
    - Win rate (closed positions)
    - Average hold time
    - Current open position count + total exposure %
    - Best trade / worst trade

- [ ] `BE` Register `bot.router` in `main.py` at `/api/v1/bot`

#### FE — `/bot/paper` page
- [ ] `FE` Create `frontend/app/bot/paper/page.tsx`:

  **Layout — 3 sections:**

  **Section 1: Bot Status Banner**
  ```
  ┌─────────────────────────────────────────────────────────────────┐
  │  🤖 Paper Trading Bot     ● ACTIVE   [■ Halt Bot]  [⚙ Settings] │
  │  Portfolio: €10,000  ·  Deployed: €3,240 (32.4%)               │
  │  Paper PnL: +€142.30 (+1.42%)  ·  Win rate: 61%  ·  7 trades   │
  └─────────────────────────────────────────────────────────────────┘
  ```
  - Red "HALTED" state when halt_flag=True with [Resume] button
  - "INACTIVE" state with [Enable Bot] when is_enabled=False

  **Section 2: Open Positions table**
  ```
  Symbol | Grade | Entry $ | Current $ | PnL % | Size | Since
  AAPL   | A+    | $182.50 | $186.20   | +2.0% | €800 | 3h ago
  NVDA   | A     | $421.00 | $419.80   | -0.3% | €600 | 1d ago
  ```
  - Refresh button polls `/bot/positions` every 60s
  - Each row: [Close Position] button → POST /bot/halt with symbol (manual close)

  **Section 3: Audit Log**
  - Last 50 log entries in a table: Time | Symbol | Action | Grade | Price | Reason
  - Colour coded: BUY=emerald, SELL=rose, HOLD=slate, SKIP=slate-dim, HALT=amber
  - Filter by symbol dropdown

  **Settings slide-over** (opens on ⚙ click):
  - Strategy: Aggressive / Balanced / Conservative pill selector
  - Minimum Grade: A+ / A / B pill selector
  - Max position size: slider 5–25% with value label
  - Max total deployed: slider 40–100%
  - Daily loss limit: slider 1–10%
  - Starting paper portfolio value: number input
  - [Save Settings] button

- [ ] `FE` Add "🤖 Bot" to Nav under Tools section (with BETA badge)
- [ ] `FE` Add `fetchBotConfig()`, `fetchBotPositions()`, `fetchBotAuditLog()`, `fetchBotPerformance()`, `haltBot()`, `enableBot()` to `lib/api.ts`

#### FE — Notification for bot actions
- [ ] `FE` When `job_bot_evaluate` fires a BUY or SELL, create an in-app alert (use existing `Alert` model with `alert_type='bot_action'`)
- [ ] `BE` In `evaluate_symbol()`: after BUY/SELL, call `create_alert(db, user_id, alert_type='bot_action', message=reason, symbol=symbol)`
- [ ] `FE` `alerts/page.tsx`: render bot_action alerts with 🤖 prefix and emerald/rose colour

### Migration
```bash
alembic revision --autogenerate -m "add_bot_tables"
alembic upgrade head
```

### Files Created
```
backend/app/models/bot.py                          # BotConfig, BotPosition, BotAuditLog ORM
backend/app/services/bot_service.py               # Decision engine + evaluate_symbol()
backend/app/services/bot_scheduler.py             # Job wrapper for scheduler
backend/app/api/v1/endpoints/bot.py               # All bot API endpoints
backend/alembic/versions/s47_001_bot_tables.py    # Migration
frontend/app/bot/paper/page.tsx                   # Paper trading UI
```

### Files Modified
```
backend/app/models/__init__.py                    # Register BotConfig, BotPosition, BotAuditLog
backend/app/main.py                               # Register bot.router
backend/app/services/scheduler.py                # Register job_bot_evaluate
frontend/components/Nav.tsx                       # Add Bot link (BETA)
frontend/lib/api.ts                               # Bot API helpers
```

---

## ✅ Sprint 48 — Lifestyle Finance: Banking & Estate Pages
**Priority:** MEDIUM — completes the Lifestyle Finance hub started in Sprint 45
**Sources:** todos-v3.md §21 NOMAD-04
**Completed:** April 2026

### Delivered
- [x] **`frontend/app/lifestyle/banking/page.tsx`** — International Banking guide: multi-currency accounts (Wise/Revolut/IBKR), SEPA vs SWIFT, FATCA, non-resident account opening, brokerage for non-residents. All sections rendered as expandable accordion cards with disclaimer.
- [x] **`frontend/app/lifestyle/estate/page.tsx`** — Estate & Pension guide: cross-border inheritance (EU 650/2012), pension portability (QROPS/SIPP), succession planning, tax-efficient wrappers by country. Same accordion pattern.
- [x] **`frontend/app/lifestyle/page.tsx`** — `disabled: true` removed from both Banking and Estate pillar cards.

### Goal
Complete the two "coming soon" pillars in the `/lifestyle` hub:
- `/lifestyle/banking` — International Banking & Investing guide
- `/lifestyle/estate` — Estate & Pension planning guide

Both are purely frontend content pages (no backend needed).

### Deliverables

#### `/lifestyle/banking` — International Banking Guide
- [x] `FE` Create `frontend/app/lifestyle/banking/page.tsx`:

  **Content sections (checklist format with expandable detail):**

  1. **Multi-Currency Accounts**
     - Wise (formerly TransferWise): best for EUR/USD/GBP movement, real exchange rate, no hidden fees
     - Revolut: good for crypto + stock investing in one place, limited banking licence
     - Interactive Brokers: best for serious multi-currency investing, cheapest FX conversion
     - IBKR has full EU banking licence, SIPC + FSCS protected

  2. **SEPA vs SWIFT**
     - SEPA: Euro transfers within EU/EEA, usually same-day, near-zero cost
     - SWIFT: International wire, $15–50 per transfer, 1–5 business days
     - When to use each: practical decision tree

  3. **FATCA Exposure for US Persons**
     - US persons must report all foreign accounts > $10,000 (FBAR Form FinCEN 114)
     - FATCA Form 8938 for assets > $50,000
     - Many European banks now refuse US persons — list of banks that still accept
     - Renunciation process (for extreme cases)

  4. **Non-Resident Account Opening**
     - Which countries allow non-resident accounts: Georgia, UAE, Switzerland, Singapore
     - Typical documents required: passport, proof of address, income source
     - Digital-first banks that accept non-residents: Wise, Revolut, Monese

  5. **Brokerage for Non-Residents**
     - Interactive Brokers: best option globally, accepts almost all nationalities
     - Trade Republic: German licence, available in 17 EU countries
     - Degiro: Dutch, EU regulated, no crypto
     - Restriction: US citizens cannot use most EU brokers (SEC rules)

  **UI pattern:**
  - Each section is an expandable accordion card (closed by default)
  - Each has a summary line visible when collapsed
  - "Practical checklist" bullet points inside each
  - Disclaimer at bottom: "Not financial or legal advice. Banking rules change frequently."

- [x] `FE` Update `frontend/app/lifestyle/page.tsx`: remove `disabled: true` from the Banking pillar card

#### `/lifestyle/estate` — Estate & Pension Planning Guide
- [x] `FE` Create `frontend/app/lifestyle/estate/page.tsx`:

  **Content sections:**

  1. **Cross-Border Inheritance Rules**
     - EU Succession Regulation (EU 650/2012): allows EU citizens to elect their home country law
     - UK: separate from EU post-Brexit — UK estate taxed under UK law even if you live abroad
     - Germany: global inheritance tax on German citizens regardless of residency
     - Practical: always have a will in every country where you own assets

  2. **Pension Portability**
     - QROPS (Qualifying Recognised Overseas Pension Scheme): UK pensions transferred abroad
       - Now subject to Overseas Transfer Charge (25%) unless in same country as you
       - Still useful for: Australia, New Zealand, EU if properly structured
     - SIPP (Self-Invested Personal Pension): keep in UK if UK tax resident < 5 years
     - EU pensions: typically not portable — new pension contribution in new country required

  3. **Succession Planning**
     - Trusts for non-UK residents: only useful if assets remain in trust jurisdiction
     - Family Investment Company (FIC): popular UK structure for passing assets to children
     - Nominating beneficiaries: pensions, life insurance — must update after every country move
     - Power of Attorney: must be valid in each country separately

  4. **Tax-Efficient Pension Wrappers by Country**
     - Germany: Rürup-Rente (Basisrente) — tax-deductible contributions, good for self-employed
     - UK: ISA + SIPP — best combined tax shelter in Europe
     - UAE: no pension system — build private portfolio instead
     - Portugal NHR: 10-year flat tax — pension income potentially 0%

  **UI pattern:** same accordion card pattern as banking page

- [x] `FE` Update `frontend/app/lifestyle/page.tsx`: remove `disabled: true` from the Estate pillar card

### Files Created
```
frontend/app/lifestyle/banking/page.tsx
frontend/app/lifestyle/estate/page.tsx
```

### Files Modified
```
frontend/app/lifestyle/page.tsx   # Remove disabled: true from Banking and Estate cards
```

---

## ✅ Sprint 49 — Activation Funnel Tracking + Engagement Gamification
**Priority:** HIGH — without this data, user acquisition and onboarding cannot be improved
**Sources:** todos-v3.md §15 (CORE-ANALYTICS-01) · todos.md §5 (streak, NPS)
**Completed:** April 2026

### Goal
Instrument the 5 key activation events in PostHog. Add a learning streak system and NPS survey.
These collectively close the biggest gap in product analytics — we currently have no idea where users drop off.

### Deliverables

#### Activation Funnel Events (PostHog)
- [x] `FE` Verify PostHog is initialised correctly in `layout.tsx` — if not, add:
  ```typescript
  // frontend/lib/posthog.ts
  import posthog from "posthog-js";
  export function initPostHog() {
      if (typeof window !== "undefined" && process.env.NEXT_PUBLIC_POSTHOG_KEY) {
          posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY, {
              api_host: "https://app.posthog.com",
              capture_pageview: true,
              capture_pageleave: true,
          });
      }
  }
  ```

- [x] `FE` Instrument these 5 activation events — fire `posthog.capture()` at each:

  **Event 1: `ticker_searched`**
  - Where: `GlobalTickerSearch.tsx` — when user selects a result from dropdown
  - Properties: `{ symbol, query, result_rank }`

  **Event 2: `gas_explain_opened`**
  - Where: `MarketWeatherWidget.tsx` or dashboard `page.tsx` — when user opens GAS explanation
  - Properties: `{ symbol, gas_score, grade }`

  **Event 3: `first_backtest_run`**
  - Where: `backtesting/page.tsx` — on first successful backtest result render
  - Properties: `{ strategy, symbol, sharpe_ratio }` — only fire once per user (check localStorage flag)

  **Event 4: `macro_page_visited`**
  - Where: `macro/page.tsx` — on component mount (useEffect once)
  - Properties: `{ source: "nav" | "dashboard_link" }`

  **Event 5: `watchlist_item_added`**
  - Where: `watchlist.py` backend AND/OR `WatchlistWidget.tsx` frontend — when symbol added
  - Properties: `{ symbol, watchlist_size_after }`
  - Note: also fire `posthog.identify(user.id, { email: user.email })` on login

- [x] `FE` Add `NEXT_PUBLIC_POSTHOG_KEY` to `.env.local` example
- [x] `FE` Create `frontend/lib/posthog.ts` with `trackEvent(name, props)` helper that no-ops when key unset

#### Learning Streak System
- [x] `BE` Add to `User` model:
  - `login_streak_days INTEGER NOT NULL DEFAULT 0` — consecutive days logged in
  - `longest_streak_days INTEGER NOT NULL DEFAULT 0` — all-time record
  - `last_streak_date DATE` — date of last login counted toward streak
- [x] `DB` Migration: `s49_001_streak_fields.py`
- [x] `BE` In auth service `login()` function: after successful login, update streak:
  ```python
  today = date.today()
  if user.last_streak_date == today - timedelta(days=1):
      user.login_streak_days += 1          # consecutive day
  elif user.last_streak_date == today:
      pass                                  # already counted today
  else:
      user.login_streak_days = 1           # streak broken, restart
  user.longest_streak_days = max(user.longest_streak_days, user.login_streak_days)
  user.last_streak_date = today
  user.last_login = datetime.now(timezone.utc)
  ```
- [x] `BE` Expose `login_streak_days` + `longest_streak_days` in `GET /auth/me` response
- [x] `FE` In `frontend/components/Nav.tsx` (or `UserMenu`): show streak badge when streak ≥ 3:
  ```
  🔥 7-day streak
  ```
  - Emerald for streaks ≥ 7 days, amber for 3–6, hidden for < 3
  - Tooltip: "You've logged in N days in a row. Keep it up!"
- [x] `FE` In `frontend/app/settings/page.tsx`: show streak stats in Profile section:
  - "Current streak: 12 days 🔥"
  - "Longest streak: 23 days"

#### NPS Survey (In-App)
- [x] `FE` Create `frontend/components/NpsSurvey.tsx`:
  - Trigger: fires on 7th session OR after 30 days, whichever comes first
  - Track session count in localStorage: increment on each page load, check on mount
  - Check `localStorage.getItem("nps_submitted")` — do not show if already answered
  - UI: slide-up panel at bottom of screen (does not block content):
    ```
    How likely are you to recommend Fin-Eye to a friend? (0–10)
    [0] [1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
    [Optional: What's the main reason for your score?       ]
    [Submit]  [Not now — ask me later]
    ```
  - On submit: `posthog.capture("nps_submitted", { score, comment, days_since_signup })`
  - Set `localStorage.setItem("nps_submitted", "true")`
- [x] `FE` Mount `<NpsSurvey />` in `frontend/app/layout.tsx` (inside AuthProvider, outside ConsentGate)

### Migration
```bash
alembic revision --autogenerate -m "add_streak_fields"
alembic upgrade head
```

### Files Created
```
frontend/lib/posthog.ts
frontend/components/NpsSurvey.tsx
backend/alembic/versions/s49_001_streak_fields.py
```

### Files Modified
```
frontend/app/layout.tsx                       # Mount NpsSurvey, init PostHog
frontend/components/GlobalTickerSearch.tsx    # Fire ticker_searched
frontend/components/Nav.tsx                   # Streak badge in UserMenu
frontend/app/settings/page.tsx               # Streak stats in profile
frontend/app/macro/page.tsx                   # Fire macro_page_visited
frontend/app/backtesting/page.tsx            # Fire first_backtest_run
backend/app/models/user.py                    # Streak fields
backend/app/services/auth_service.py         # Streak update on login
```

---

## ✅ Sprint 50 — Referral Program + Social Proof
**Priority:** MEDIUM — viral growth lever, low build cost
**Sources:** todos.md §5 "Referral Program"
**Completed:** April 2026

### Goal
Build a referral system: each user gets a unique referral link. When a referred user upgrades to Pro, the referrer gets 1 month free. Add social proof to the billing page.

### Deliverables

#### Referral System Backend
- [ ] `DB` Migration `s50_001_referrals.py`:
  ```sql
  ALTER TABLE users ADD COLUMN referral_code VARCHAR(12) UNIQUE;
  ALTER TABLE users ADD COLUMN referred_by   UUID REFERENCES users(id);
  ALTER TABLE users ADD COLUMN referral_credits_months INTEGER NOT NULL DEFAULT 0;

  CREATE TABLE referral_events (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id  UUID REFERENCES users(id) NOT NULL,
    referred_id  UUID REFERENCES users(id) NOT NULL UNIQUE,
    event        VARCHAR(20) NOT NULL,  -- 'signup' | 'upgrade'
    credited_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  ```

- [ ] `BE` In `auth_service.py` `register()`:
  - Generate unique 8-char referral code: `secrets.token_urlsafe(6)` (URL-safe, 8 chars)
  - If `?ref=CODE` query param present in registration URL: look up referrer by code, set `User.referred_by`
  - Insert `referral_events(referrer_id, referred_id, event='signup')`

- [ ] `BE` In billing service when user upgrades to Pro:
  - Check `User.referred_by` — if set and `referral_events` has signup but not upgrade:
  - Insert `referral_events(event='upgrade', credited_at=now())`
  - Increment referrer's `referral_credits_months += 1`
  - Extend referrer's Pro subscription by 1 month (update `trial_ends_at` or create credit record)
  - Send email to referrer: "Your friend upgraded! You've earned 1 free month."

- [ ] `BE` Endpoints in `billing.py` (or new `referral.py`):
  - `GET /api/v1/referral/my-code` — returns user's referral code + link + stats
    ```json
    { "code": "abc12xyz", "link": "https://fin-eye.app?ref=abc12xyz", 
      "signups": 3, "upgrades": 1, "credits_earned": 1 }
    ```
  - `GET /api/v1/referral/leaderboard` — top 10 referrers (anonymised) for social proof

#### Referral Frontend
- [ ] `FE` Create `frontend/app/referral/page.tsx`:
  - "Invite friends, earn free Pro" header
  - Referral link box with copy button
  - Stats: "3 friends signed up · 1 upgraded · 1 free month earned"
  - Referral leaderboard (top 10 anonymised: "joh*** — 5 referrals")
  - How it works: 3 steps with icons
  - Share buttons: copy link, share via email (mailto:), share via WhatsApp

- [ ] `FE` Add referral link to Nav: "💰 Earn Free Pro" under Learn section (only when user is free tier)

#### Social Proof on Billing Page
- [ ] `FE` In `frontend/app/billing/page.tsx`, add a social proof section above the plan cards:
  ```
  ★★★★★  "Finally understand what's moving the markets"
  ★★★★☆  "The GAS score is eerily accurate"
  ★★★★★  "Best €14.99 I spend each month"
  
  Join 1,200+ investors using Fin-Eye
  ```
  - 3 hardcoded testimonials (real or placeholder until real reviews gathered)
  - User count badge (hardcode realistic number, update monthly)

### Migration
```bash
alembic upgrade head   # s50_001_referrals
```

### Files Created
```
frontend/app/referral/page.tsx
backend/alembic/versions/s50_001_referrals.py
```

### Files Modified
```
backend/app/models/user.py          # referral_code, referred_by, referral_credits_months
backend/app/services/auth_service.py # Generate referral code on register, link referrer
backend/app/api/v1/endpoints/billing.py  # Referral endpoints
frontend/app/billing/page.tsx       # Social proof section
frontend/components/Nav.tsx         # Referral link for free users
```

---

## ✅ Sprint 51 — TypeScript Strict Mode + Lighthouse CI
**Priority:** MEDIUM — technical debt that prevents bugs reaching production
**Sources:** todos.md §4 · todos-v3.md §12
**Completed:** April 2026

### Goal
Enable TypeScript strict mode and fix all resulting type errors. Set up automated Lighthouse CI
on GitHub Actions gating merges on Performance ≥ 85 and Accessibility ≥ 90.

### Deliverables

#### TypeScript Strict Mode
- [ ] `FE` In `frontend/tsconfig.json`, change:
  ```json
  {
    "compilerOptions": {
      "strict": true,
      "noImplicitAny": true,
      "strictNullChecks": true,
      "strictFunctionTypes": true,
      "noUnusedLocals": true,
      "noUnusedParameters": false
    }
  }
  ```
- [ ] `FE` Run `tsc --noEmit` and systematically fix all errors. Common patterns to fix:
  - Replace `any` in `lib/api.ts` with proper typed DTOs
  - Add null checks where SWR data might be undefined
  - Fix implicit `any` in event handlers: `(e) => ...` → `(e: React.ChangeEvent<HTMLInputElement>) => ...`
  - Add explicit return types to all async functions in `lib/api.ts`
  - Fix `as any` casts — replace with proper type assertions or generics
- [ ] `FE` Fix TypeScript errors file by file, starting with highest-impact: `lib/api.ts` → `app/page.tsx` → component files
- [ ] `FE` Run `tsc --noEmit` until zero errors
- [ ] Document: which `any` types were intentionally kept (with `// eslint-disable-next-line @typescript-eslint/no-explicit-any`) and why

#### Lighthouse CI
- [ ] Create `.github/workflows/lighthouse.yml`:
  ```yaml
  name: Lighthouse CI
  on:
    pull_request:
      branches: [main]
  jobs:
    lighthouse:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-node@v4
          with: { node-version: '20' }
        - run: npm ci
          working-directory: frontend
        - run: npm run build
          working-directory: frontend
        - name: Run Lighthouse CI
          uses: treosh/lighthouse-ci-action@v11
          with:
            urls: |
              http://localhost:3000
              http://localhost:3000/macro
              http://localhost:3000/backtesting
            budgetPath: ./frontend/lighthouse-budget.json
            uploadArtifacts: true
  ```

- [ ] Create `frontend/lighthouse-budget.json`:
  ```json
  [
    {
      "path": "/*",
      "timings": [{ "metric": "first-contentful-paint", "budget": 3000 }],
      "resourceSizes": [{ "resourceType": "script", "budget": 400 }],
      "resourceCounts": [{ "resourceType": "total", "budget": 100 }]
    }
  ]
  ```

- [ ] Create `frontend/lighthouserc.json`:
  ```json
  {
    "ci": {
      "assert": {
        "assertions": {
          "categories:performance": ["error", {"minScore": 0.85}],
          "categories:accessibility": ["error", {"minScore": 0.90}],
          "categories:best-practices": ["warn", {"minScore": 0.85}],
          "categories:seo": ["warn", {"minScore": 0.80}]
        }
      }
    }
  }
  ```

- [ ] Fix any Lighthouse failures that block the gate — common issues:
  - Missing `alt` attributes on images
  - Colour contrast failures (use results of Sprint 43 contrast audit)
  - Missing `lang` attribute on `<html>` (should already be there)
  - Render-blocking resources
  - Missing meta description

### Files Created
```
.github/workflows/lighthouse.yml
frontend/lighthouse-budget.json
frontend/lighthouserc.json
```

### Files Modified
```
frontend/tsconfig.json             # Enable strict mode
frontend/lib/api.ts                # Fix all any types
frontend/app/page.tsx              # Fix implicit any + null checks
All other TypeScript files         # Fix remaining errors
```

---

## ✅ Sprint 52 — Discussion Threads + Bull vs Bear Poll
**Priority:** MEDIUM — community engagement, daily habit loop
**Sources:** todos.md §12 · todos-v3.md §23
**Completed:** April 2026

### Goal
Add per-ticker discussion threads (brief comments on analysis pages) and a weekly
Bull vs Bear poll on SPY to create a Monday habit loop.

### Deliverables

#### Discussion Threads
- [x] `DB` Migration `s52_001_discussions.py`:
  ```sql
  CREATE TABLE ticker_comments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    symbol       VARCHAR(20) NOT NULL,
    body         TEXT NOT NULL CHECK (length(body) BETWEEN 10 AND 500),
    is_deleted   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
  );
  CREATE INDEX idx_tc_symbol_time ON ticker_comments(symbol, created_at DESC);

  CREATE TABLE ticker_comment_reactions (
    comment_id  UUID REFERENCES ticker_comments(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    reaction    VARCHAR(10) NOT NULL DEFAULT 'up',  -- 'up' | 'down'
    PRIMARY KEY (comment_id, user_id)
  );
  ```

- [x] `BE` Create `backend/app/api/v1/endpoints/comments.py`:

  `GET /api/v1/comments/{symbol}?limit=20&before_id=xxx`
  - Paginated, newest first
  - Each comment: id, body, username (anonymised: first 3 + ***), created_at, upvotes, downvotes, user_reaction
  - Filter: `is_deleted=False`

  `POST /api/v1/comments/{symbol}`
  - Auth required + verified
  - Body: `{ "body": "..." }` (10–500 chars, validated server-side)
  - Rate limit: max 10 comments per user per hour (slowapi)
  - Basic moderation: reject if body contains banned words list (configurable)

  `DELETE /api/v1/comments/{comment_id}`
  - Author or admin only
  - Soft delete: sets `is_deleted=True`, body replaced with "[deleted]"

  `POST /api/v1/comments/{comment_id}/react`
  - Body: `{ "reaction": "up" | "down" }`
  - Upserts `ticker_comment_reactions` — toggle if same reaction

- [x] `BE` Register `comments.router` in `main.py` at `/api/v1/comments`

- [x] `FE` Create `frontend/components/TickerComments.tsx`:
  - Collapsible panel (collapsed by default with "N comments" label)
  - Comment list: anonymised username, relative time, body, 👍/👎 reaction buttons with counts
  - "Load more" button (pagination)
  - Text area + Submit button (shown only when authenticated + verified)
  - Character counter (500 max)
  - "Comments are moderated. Be respectful." disclaimer

- [x] `FE` Wire `TickerComments` into `frontend/app/page.tsx` dashboard — place below SocialSignalsPanel

#### Bull vs Bear Weekly Poll
- [x] `DB` Migration `s52_002_polls.py`:
  ```sql
  CREATE TABLE weekly_polls (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_number  INTEGER NOT NULL,  -- ISO week number
    year         INTEGER NOT NULL,
    symbol       VARCHAR(20) NOT NULL DEFAULT 'SPY',
    question     TEXT NOT NULL,
    opens_at     TIMESTAMPTZ NOT NULL,
    closes_at    TIMESTAMPTZ NOT NULL,
    UNIQUE(week_number, year, symbol)
  );

  CREATE TABLE poll_votes (
    poll_id    UUID REFERENCES weekly_polls(id) ON DELETE CASCADE,
    user_id    UUID REFERENCES users(id) ON DELETE CASCADE,
    vote       VARCHAR(10) NOT NULL,  -- 'bullish' | 'bearish' | 'neutral'
    voted_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (poll_id, user_id)
  );
  ```

- [x] `BE` In `scheduler.py`: add `job_create_weekly_poll` — runs Monday 00:01 UTC
  - Creates a `weekly_polls` row for the current week + SPY
  - Question: "Are you Bullish, Bearish, or Neutral on SPY this week?"
  - `closes_at` = following Sunday 23:59 UTC

- [x] `BE` Endpoints in new `backend/app/api/v1/endpoints/polls.py`:

  `GET /api/v1/polls/current` — returns current week's poll + vote counts + user's vote
  ```json
  { "poll_id": "...", "question": "...", "closes_at": "...",
    "results": { "bullish": 342, "bearish": 128, "neutral": 89, "total": 559 },
    "user_vote": "bullish" }
  ```

  `POST /api/v1/polls/{poll_id}/vote`
  - Body: `{ "vote": "bullish" | "bearish" | "neutral" }`
  - One vote per user per poll (upsert)
  - Returns updated vote counts

- [x] `FE` Create `frontend/components/WeeklyPoll.tsx`:
  - Monday-activated pill component on dashboard (show only Mon–Fri, or if user hasn't voted)
  - Before vote: "🗳️ This week's poll: Are you bullish on SPY?" + 3 vote buttons (emerald/rose/amber)
  - After vote: donut chart showing % bullish/bearish/neutral + "559 investors voted"
  - Coloured breakdown: "Bullish 61% · Bearish 23% · Neutral 16%"

- [x] `FE` Wire `WeeklyPoll` into dashboard `page.tsx` — place in sidebar above EarningsCalendarStrip

### Migration
```bash
alembic upgrade head   # s52_001_discussions + s52_002_polls
```

### Files Created
```
backend/app/api/v1/endpoints/comments.py
backend/app/api/v1/endpoints/polls.py
backend/alembic/versions/s52_001_discussions.py
backend/alembic/versions/s52_002_polls.py
frontend/components/TickerComments.tsx
frontend/components/WeeklyPoll.tsx
```

### Files Modified
```
backend/app/main.py        # Register comments.router + polls.router
backend/app/services/scheduler.py  # job_create_weekly_poll
frontend/app/page.tsx      # Wire TickerComments + WeeklyPoll
frontend/lib/api.ts        # fetchComments(), postComment(), voteOnPoll() etc.
```

---

## ✅ Sprint 53 — Shareable GAS Report Card (PNG/PDF Export)
**Priority:** MEDIUM — viral distribution mechanism
**Sources:** todos.md §7 "Shareable GAS Report Card"
**Completed:** April 2026

### Goal
Add a "Share Analysis" button on the dashboard that generates a branded PNG card
showing GAS score, grade, regime, key signals, and disclaimer. Shareable to Twitter/X, LinkedIn, WhatsApp.

### Deliverables

#### Backend — PDF/Image Generation
- [x] `BE` Add to `requirements.txt`: `playwright>=1.40.0` or `weasyprint>=61.0` (for HTML→PDF)
  - Recommendation: use `playwright` for pixel-perfect PNG rendering of an HTML template
  - Alternative: build entirely client-side with `html2canvas` npm package (no backend needed)
  - Decision: **client-side with `html2canvas`** (simpler, no server resources, no playwright install)

#### Frontend — Report Card Component
- [x] `FE` Create `frontend/components/GasReportCard.tsx`:
  - Hidden off-screen div rendered with fixed 800×450px dimensions (Twitter card ratio)
  - Content:
    ```
    ┌──────────────────────────────────────────────────────────────┐
    │  fin-eye                              2026-04-12             │
    │                                                               │
    │  AAPL · Apple Inc.                                           │
    │                                                               │
    │  GAS Score  74/100    Grade  A    Regime  Risk-On            │
    │  ████████████████████░░░░░                                    │
    │                                                               │
    │  Technical ↑ Bullish (1d, 67%)                               │
    │  Sentiment ↑ Bullish (7d avg)                                │
    │  Macro     → Neutral (score 58)                              │
    │                                                               │
    │  ⚠ For educational purposes only. Not financial advice.      │
    │  Generated by fin-eye.app                                    │
    └──────────────────────────────────────────────────────────────┘
    ```
  - Fin-Eye brand colours: `bg-slate-950`, emerald/sky/amber accents
  - Logo text "fin-eye" in top-left (no external image dependency)

- [x] `FE` Add `html2canvas` to `frontend/package.json`:
  ```bash
  npm install html2canvas
  ```

- [x] `FE` In `frontend/app/page.tsx` dashboard, add "Share Analysis" button in the dashboard header area:
  ```typescript
  const handleShare = async () => {
      const canvas = await html2canvas(document.getElementById("gas-report-card")!);
      const blob = await new Promise<Blob>(resolve => canvas.toBlob(resolve!, "image/png"));
      
      // Method 1: Download PNG
      const link = document.createElement("a");
      link.download = `fin-eye-${activeSymbol}-${new Date().toISOString().slice(0,10)}.png`;
      link.href = URL.createObjectURL(blob);
      link.click();
      
      // Method 2: Web Share API (mobile)
      if (navigator.share) {
          await navigator.share({
              title: `${activeSymbol} GAS Score: ${gasScore}/100`,
              text: `${activeSymbol} has a GAS score of ${gasScore}/100 (Grade ${grade}) on Fin-Eye`,
              files: [new File([blob], "fin-eye-analysis.png", { type: "image/png" })]
          });
      }
  };
  ```

- [x] `FE` "Share" button in dashboard header: `<Share2 className="h-4 w-4" /> Share Analysis`
  - Shows a small dropdown: [📥 Download PNG] [🐦 Share on X] [💼 Share on LinkedIn] [📱 Share via Device]
  - Twitter/X share: `https://twitter.com/intent/tweet?text=...&url=https://fin-eye.app`
  - LinkedIn share: `https://www.linkedin.com/sharing/share-offsite/?url=...`

### Files Created
```
frontend/components/GasReportCard.tsx
```

### Files Modified
```
frontend/app/page.tsx       # Share button + handleShare() function
frontend/package.json       # Add html2canvas
```

---

## ✅ Sprint 54 — Bond Ladder Builder
**Priority:** LOW-MEDIUM — completes the investment planning toolkit
**Sources:** todos-v3.md §20 PLAN-06 · todos.md §18
**Completed:** April 2026

### Delivered
- [x] **`backend/app/api/v1/endpoints/macro.py`** — `GET /api/v1/macro/bond-ladder?total_investment=N&currency=X` endpoint added. Fetches 8 FRED Treasury yield series (DGS1MO→DGS30), computes equal-split allocation, blended yield, total annual income, and curve shape (Normal/Inverted/Flat/Unknown). Returns structured `BondLadderDto`.
- [x] **`frontend/app/portfolio/bond-ladder/page.tsx`** — Full page: investment amount input, EUR/USD/GBP currency toggle, "Build Ladder" button. Results: 3 KPI tiles (blended yield, total annual income, curve shape), Recharts bar chart with per-maturity gradient colours, allocation table (Maturity / Yield / Allocation / Annual Income), link back to `/macro`, and educational disclaimer.
- [x] **`frontend/lib/api.ts`** — `BondLadderRung`, `BondLadderDto` TypeScript types + `fetchBondLadder(investment, currency)` function added.
- [x] **`frontend/app/macro/page.tsx`** — "Build a bond ladder with these yields →" link added to the Advanced Macro view (line 844).
- [x] **`frontend/components/Nav.tsx`** — "Bond Ladder" added to Tools section with NEW badge at line 83. Directly accessible from sidebar — no `/portfolio/page.tsx` hub needed.

### Note on `/portfolio/page.tsx`
No top-level `/portfolio` hub page exists or was needed. The Bond Ladder is discoverable via:
1. The sidebar nav (Tools → Bond Ladder)
2. The `/macro` Advanced view deep-link

### Files Created
```
frontend/app/portfolio/bond-ladder/page.tsx
```

### Files Modified
```
backend/app/api/v1/endpoints/macro.py   # GET /api/v1/macro/bond-ladder endpoint
frontend/app/macro/page.tsx             # Deep-link to bond ladder
frontend/lib/api.ts                     # BondLadderRung, BondLadderDto, fetchBondLadder()
frontend/components/Nav.tsx             # Bond Ladder nav item with NEW badge
```

---

## Sprint 55 — Per-Seat B2B Billing + Tenant Compliance Export
**Priority:** LOW — only needed once B2B advisor pipeline has first tenants
**Sources:** todos-v3.md §22 (B2B-BILLING-01, B2B-COMPLIANCE-01 export)

### Goal
Add Stripe metered billing for advisor tenant tiers (Starter/Growth/Enterprise).
Add `GET /admin/compliance/export` endpoint returning paginated CSV of audit log.

### Deliverables

#### B2B Billing Tiers
- [x] `DB` Migration `s55_001_tenant_billing.py`:
  ```sql
  ALTER TABLE tenants ADD COLUMN tier VARCHAR(20) NOT NULL DEFAULT 'starter';
    -- 'starter' (≤10 seats), 'growth' (≤50 seats), 'enterprise' (unlimited)
  ALTER TABLE tenants ADD COLUMN seat_count INTEGER NOT NULL DEFAULT 1;
  ALTER TABLE tenants ADD COLUMN stripe_customer_id VARCHAR(100);
  ALTER TABLE tenants ADD COLUMN stripe_subscription_id VARCHAR(100);
  ALTER TABLE tenants ADD COLUMN billing_cycle_end TIMESTAMPTZ;

  CREATE TABLE tenant_seats (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID REFERENCES tenants(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL DEFAULT 'member',  -- 'owner' | 'admin' | 'member'
    invited_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    accepted_at TIMESTAMPTZ,
    UNIQUE(tenant_id, user_id)
  );
  ```

- [x] `BE` In `tenants.py` endpoints:

  `POST /api/v1/tenants/{slug}/invite`
  - Body: `{ "email": "advisor@firm.com", "role": "member" }`
  - Creates invitation email via Resend with accept link
  - Validates seat count ≤ tier limit

  `GET /api/v1/tenants/{slug}/seats`
  - Returns list of all seats: user email, role, accepted status

  `DELETE /api/v1/tenants/{slug}/seats/{user_id}`
  - Owner/admin only — removes seat

  `GET /api/v1/tenants/{slug}/billing`
  - Returns tier, seat_count, billing_cycle_end, Stripe portal URL

- [x] `BE` Stripe webhook handler for tenant billing:
  - `customer.subscription.created` → set `stripe_subscription_id`, `billing_cycle_end`, `tier`
  - `customer.subscription.deleted` → downgrade to `starter`, 0 seats
  - `invoice.paid` → extend `billing_cycle_end`

#### Compliance Audit Log Export
- [x] `BE` In new `backend/app/api/v1/endpoints/compliance.py`:

  `GET /api/v1/admin/compliance/export?tenant_id=xxx&from=2026-01-01&to=2026-04-01`
  - Admin or tenant owner only
  - Returns paginated list of `ComplianceAuditLog` entries
  - With `?format=csv`: streams CSV with headers: id, tenant_id, user_id, action, resource, ip_address, timestamp
  - Max export: 90 days per request (to prevent accidental huge exports)

  `GET /api/v1/admin/compliance/summary?tenant_id=xxx`
  - Returns: total calls, unique users, most-called endpoints, calls by day (last 30 days)

- [x] `FE` Create `frontend/app/admin/compliance/page.tsx`:
  - Date range picker (default: last 30 days)
  - Tenant selector (admin only — shows all tenants)
  - [Download CSV] button → calls `/admin/compliance/export?format=csv`
  - Summary stats bar: total API calls, unique users, date range
  - Log table: last 200 entries with timestamp, tenant, user, action, resource

### Migration
```bash
alembic upgrade head   # s55_001_tenant_billing
```

### Files Created
```
backend/app/api/v1/endpoints/compliance.py
backend/alembic/versions/s55_001_tenant_billing.py
frontend/app/admin/compliance/page.tsx
```

### Files Modified
```
backend/app/models/tenant.py        # tier, seat_count, stripe fields
backend/app/api/v1/endpoints/tenants.py   # invite, seats, billing endpoints
backend/app/main.py                 # Register compliance.router
frontend/lib/api.ts                 # Compliance + seat management helpers
```

---

---

## Sprint 56 — Monte Carlo: Bot Integration, Backtest Projection & UI Polish
**Priority:** HIGH — the MC engine is built but disconnected from the bot risk layer, the backtester, and the UI playground needs significant hardening.
**Sources:** Codebase audit April 2026 · User specification for financial simulations.
**Status:** Phase 2 + Phase 3 COMPLETE — April 2026

### Delivered (April 2026)
- [x] **Phase 2** — `GET /api/v1/montecarlo/vol-estimate` endpoint in `montecarlo.py`
  - Reads `adj_close` from `ohlcv_daily` table (OHLCVDaily model)
  - Computes `sigma_annual = std(log_returns) * sqrt(252)` and `mu_annual = mean(log_returns) * 252`
  - Returns `{ symbol, annualized_vol_pct, annualized_return_pct, data_days }`
  - Rate-limit: raises 404 if < 30 data points found
- [x] **api.ts** — Added full MC type suite: `MCPercentileResult`, `MCPortfolioAsset`, `MCPortfolioParams`, `MCPortfolioResult`, `MCAssetParams`, `MCSimulationResult`, `VolEstimateDto`
- [x] **api.ts** — Added `runPortfolioMonteCarlo()`, `runAssetMonteCarlo()`, `fetchVolEstimate()` helpers
- [x] **Phase 3** — Full rewrite of `frontend/app/portfolio/montecarlo/page.tsx`:
  - Asset preset templates: Balanced 60/40, All-Equity, Retirement Income
  - Single Asset vs Portfolio mode toggle (pill at top)
  - Historical vol auto-fill per asset: "Fetch" button calls `fetchVolEstimate()` → populates σ and μ
  - Correlation matrix input: N×N grid, symmetric auto-mirror, diagonal locked to 1.0, Reset button
  - Retirement mode: monthly_contribution < 0 → "withdrawal" label, success_rate KPI with colour coding, plain-English sentence
  - Scenario comparison: up to 3 runs accumulated, P50 median overlay chart with legend
  - Single-asset mode: Jump Diffusion sliders (λ, jump mean, jump σ) with educational tooltips
  - Educational tooltips on μ, σ, jump_intensity via inline `<Tip>` component
  - Disclaimer banner always visible after first run
  - Phase 1 (Bot MC-CVaR gate) — pending separate bot_service.py edit

### Files Modified
```
backend/app/api/v1/endpoints/montecarlo.py   # GET /vol-estimate + cleanup
frontend/lib/api.ts                          # Full MC type suite + 3 helpers
frontend/app/portfolio/montecarlo/page.tsx   # Complete rewrite
```

### What Already Exists (DO NOT REBUILD)
> **Audit confirmed April 2026** — verified in codebase before writing this plan.
- [x] `backend/app/services/mc_engine.py` — GBM + Merton Jump Diffusion, Cholesky correlated portfolio simulation, CVaR, percentile extraction. **Fully implemented and vectorised.**
- [x] `backend/app/schemas/montecarlo_models.py` — `MCAssetParams`, `MCPortfolioParams`, `MCSimulationResult`, `MCPortfolioResult`, `MCPercentileResult`. **Complete.**
- [x] `backend/app/api/v1/endpoints/montecarlo.py` — `POST /asset` (OOM-guarded, 50k path cap) + `POST /portfolio` (50 asset cap). **Registered in `main.py` at `/api/v1/montecarlo`.**
- [x] `frontend/lib/api.ts` — full MC TypeScript types + `runAssetMonteCarlo()` + `runPortfolioMonteCarlo()`. **Complete.**
- [x] `frontend/app/portfolio/montecarlo/page.tsx` — basic portfolio simulator with AreaChart probability cone. **Works, needs polish.**
- [x] `frontend/components/Nav.tsx` — MC Simulator already linked under Tools section.
- [x] `frontend/app/backtesting/page.tsx` — MC forward projection panel already implemented ("Simulate 3 Years" button + fan chart).

### Goal
Close the three remaining gaps: (1) wire MC CVaR risk data into the paper trading bot's BUY decision gate, (2) add a vol-estimate endpoint so the MC playground can auto-fill sigma from real OHLCV history, and (3) polish the `/portfolio/montecarlo` UI with preset templates, single-asset mode, correlation matrix input, scenario comparison, and retirement mode.

---

### Phase 1 — Bot Service: MC-CVaR Risk Gate
**Files:** `backend/app/services/bot_service.py`, `backend/app/services/mc_engine.py`

Currently `evaluate_symbol()` uses static `2×ATR` stop-loss for position sizing. Add a forward-looking MC gate that blocks new BUY positions when 30-day CVaR exceeds the user's configured `daily_loss_limit`.

- [ ] `BE` Add `compute_log_returns(prices: list[float]) -> np.ndarray` helper to `mc_engine.py` — computes `np.diff(np.log(prices))`.
- [ ] `BE` In `bot_service.py` `evaluate_symbol()`, after a BUY signal passes grade + GAS checks:
  - Fetch last 126 trading days of close prices from `ohlcv_data` table for the symbol.
  - If fewer than 30 data points: log `SKIP` with reason `"Insufficient OHLCV for MC gate"` and fall back to ATR sizing.
  - Compute `sigma_annual = std(log_returns) * sqrt(252)` and `mu_annual = mean(log_returns) * 252`.
  - Call `run_asset_simulation(MCAssetParams(symbol=symbol, starting_value=proposed_usd, mu=mu_annual, sigma=sigma_annual, years=30/365, paths=5000, steps_per_year=252, model_type="GBM"))`.
  - If `mc_result.cvar_95 > config.daily_loss_limit`: log audit entry with `action="SKIP"`, reason includes the CVaR value, and return early — no BUY.
  - The existing ATR-based stop-loss is **kept** as a real-time stop during holding. The MC gate applies only at BUY decision time.
- [ ] `BE` Add `mc_cvar_pct FLOAT` column to `bot_audit_log` migration (or store in the existing `reason` TEXT field — acceptable).
- **Test:** Set `daily_loss_limit=0.01`, run `evaluate_symbol()` on a high-vol symbol → expect SKIP with CVaR reason. Low-vol symbol at same limit → BUY proceeds.

### Phase 2 — New Vol-Estimate Endpoint
**File:** `backend/app/api/v1/endpoints/montecarlo.py`

The MC playground UI needs to be able to auto-fill sigma/mu from real data. Add a lightweight read-only endpoint.

- [ ] `BE` Add `GET /api/v1/montecarlo/vol-estimate?symbol=AAPL&days=252`:
  ```python
  @router.get("/vol-estimate")
  def get_vol_estimate(symbol: str, days: int = 252, db: Session = Depends(get_db)):
      ohlcv = get_recent_ohlcv_sync(db, symbol.upper(), days=days)
      if len(ohlcv) < 30:
          raise HTTPException(404, f"Insufficient OHLCV for {symbol}")
      log_returns = np.diff(np.log([r.close for r in ohlcv]))
      return {
          "symbol": symbol.upper(),
          "annualized_vol_pct": round(float(log_returns.std() * np.sqrt(252)), 4),
          "annualized_return_pct": round(float(log_returns.mean() * 252), 4),
          "data_days": len(ohlcv),
      }
  ```
  - Rate-limit: 20 requests/minute (read-only, lightweight).
- [ ] `FE` Add `fetchVolEstimate(symbol: string, days?: number): Promise<{ symbol: string; annualized_vol_pct: number; annualized_return_pct: number; data_days: number }>` to `lib/api.ts`.

### Phase 3 — MC Playground UI Polish
**File:** `frontend/app/portfolio/montecarlo/page.tsx`

The existing page works but is sparse. This phase makes it a professional quant tool.

- [ ] `FE` **Asset preset templates** — add "Load Preset" pill strip above asset list:
  - Balanced 60/40: Stocks (mu=0.10, sigma=0.18, 60%) + Bonds (mu=0.04, sigma=0.08, 40%)
  - All-Equity: US Stocks (mu=0.10, sigma=0.18, 70%) + International (mu=0.07, sigma=0.16, 30%)
  - Retirement Income: Bonds 50% + Dividend Equities 30% + Cash (mu=0.05, sigma=0.01) 20%
  - Presets populate all asset fields instantly on click.

- [ ] `FE` **Single-asset mode toggle** — `[Single Asset]  [Portfolio]` pill at top:
  - Single asset: calls `runAssetMonteCarlo()`, exposes model selector (GBM vs Jump Diffusion), shows jump parameter sliders when JD selected, adds CVaR-95 KPI block.
  - Portfolio: existing `runPortfolioMonteCarlo()` flow.

- [ ] `FE` **Historical vol auto-fill** — next to each asset's sigma field, small "🔍 Fetch" button:
  - Calls `fetchVolEstimate(symbol, 252)` → populates sigma and mu inputs automatically.
  - Disabled when symbol field is empty.

- [ ] `FE` **Correlation matrix input** — collapsible section shown when ≥2 assets in Portfolio mode:
  - N×N grid of number inputs, pre-filled `0.0`, diagonal locked to `1.0` (greyed out).
  - "Reset" button sets all off-diagonal to 0.
  - Passes `correlation_matrix` to `runPortfolioMonteCarlo()`.

- [ ] `FE` **Retirement mode** — when `monthly_contribution < 0` (withdrawal):
  - Label changes to "Monthly withdrawal".
  - Colour-coded `success_rate` KPI: ≥90% emerald, 70–90% amber, <70% rose.
  - Plain English description: "Your portfolio has a **{success_rate}%** chance of lasting {years} years at this withdrawal rate."

- [ ] `FE` **Scenario comparison** — "Add Scenario" button accumulates up to 3 runs and overlays their P50 median lines on the same chart with distinct colours and a legend.

- [ ] `FE` **Educational tooltips** — add `title` attributes to all parameter inputs:
  - `mu` → "Expected annual return (e.g. 0.10 = 10% per year). Historical average for US equities ~7–10%."
  - `sigma` → "Annual volatility (e.g. 0.18 = 18% standard deviation). Higher = more uncertainty."
  - `jump_intensity` → "Expected crashes per year. US equities experience ~2–3 major drops annually."

- [ ] `FE` **Disclaimer banner** — always visible at bottom of page:
  ```
  ⚠ Monte Carlo projections use historical parameters to generate hypothetical future scenarios.
  They do not account for taxes, fees, or black swan events. For educational planning only — not investment advice.
  ```

### No New DB Migration Required
All computation is stateless (in-memory per request). All data reads from the existing `ohlcv_data` table.

### Files Modified
```
backend/app/services/mc_engine.py            # compute_log_returns() helper
backend/app/services/bot_service.py          # MC-CVaR gate in evaluate_symbol()
backend/app/api/v1/endpoints/montecarlo.py   # GET /vol-estimate endpoint
frontend/app/portfolio/montecarlo/page.tsx   # Presets, single-asset, correlation, scenario compare
frontend/lib/api.ts                          # fetchVolEstimate()
```

### Verification Checklist
```
[ ] Bot: evaluate_symbol() on high-vol symbol with low daily_loss_limit → SKIP with CVaR reason in audit log
[ ] Bot: evaluate_symbol() on low-vol symbol with normal limit → BUY proceeds normally
[ ] GET /api/v1/montecarlo/vol-estimate?symbol=AAPL → returns sigma/mu/data_days
[ ] MC Playground: load "Balanced 60/40" preset → asset fields populate instantly
[ ] MC Playground: enter "AAPL" + click Fetch → sigma/mu auto-fill from OHLCV
[ ] MC Playground: switch to Single Asset → Jump Diffusion → extra sliders visible
[ ] MC Playground: negative monthly contribution → "withdrawal" label + success_rate KPI
[ ] MC Playground: Add Scenario → two runs overlaid on same chart
[ ] Backtesting: run strategy → "Simulate 3 Years" button → fan chart renders correctly
```

---

## Sprint Execution Order Summary

| Sprint | Name | Priority | Backend | Frontend | DB | Status |
|--------|------|----------|---------|----------|-----|--------|
| 46 | Security Hardening | 🔴 CRITICAL | Heavy | Light | 1 migration | ✅ Complete |
| 47 | Paper Trading Bot | 🟠 HIGH | Heavy | Heavy | 3 tables | ✅ Complete |
| 48 | Lifestyle Banking + Estate | 🟡 MEDIUM | None | Medium | None | ✅ Complete |
| 49 | Activation Tracking + Streak + NPS | 🟠 HIGH | Medium | Medium | 1 migration | ✅ Complete |
| 50 | Referral Program + Social Proof | 🟡 MEDIUM | Medium | Medium | 1 migration | ✅ Complete |
| 51 | TypeScript Strict + Lighthouse CI | 🟡 MEDIUM | None | Heavy | None | ⛔ Skipped (by decision) |
| 52 | Discussion Threads + Poll | 🟡 MEDIUM | Medium | Medium | 2 migrations | ✅ Complete |
| 53 | Shareable Report Card | 🟡 MEDIUM | None | Light | None | ✅ Complete |
| 54 | Bond Ladder Builder | 🟢 LOW-MED | Light | Medium | None | ✅ Complete |
| 55 | B2B Billing + Compliance Export | 🟢 LOW | Medium | Medium | 1 migration | ✅ Complete |
| 56 | Advanced Monte Carlo Simulation | 🟠 HIGH | Heavy | Heavy | None | ✅ Complete |

---

## Migrations by Sprint (run in order)

```bash
# Sprint 46
alembic revision -m "add_email_verification_fields"
alembic upgrade head

# Sprint 47
alembic revision -m "add_bot_tables"
alembic upgrade head

# Sprint 49
alembic revision -m "add_streak_fields"
alembic upgrade head

# Sprint 50
alembic revision -m "add_referrals"
alembic upgrade head

# Sprint 52
alembic revision -m "add_discussions_and_polls"
alembic upgrade head

# Sprint 55
alembic revision -m "add_tenant_billing_and_seats"
alembic upgrade head
```

---

## Global Rules for All Sprints

1. **Audit before building:** always check if a file exists before creating it — re-read SPRINT_PROGRESS.md notes
2. **Registration:** every new backend router must be imported in `main.py` and mounted with a prefix
3. **Migrations:** every new model must have a corresponding Alembic migration; always run `alembic upgrade head` after
4. **Model registration:** every new ORM model must be imported in `app/models/__init__.py`
5. **API types:** every new backend endpoint must have corresponding TypeScript types + fetch function in `frontend/lib/api.ts`
6. **Nav:** every new frontend page that users should discover must be added to `Nav.tsx` SIDEBAR_SECTIONS
7. **Sprint progress:** update `SPRINT_PROGRESS.md` after every sprint marking items ✅
8. **No mock data:** all new endpoints must read from real DB — never return hardcoded sample data
9. **Error handling:** every new API endpoint must handle and log exceptions; frontend must handle loading/error/empty states
10. **Educational disclaimer:** any page showing financial data must include the standard disclaimer

---

*Sprint Plans 46–55 created: April 2026 · Last updated: April 2026*
*Based on complete audit of: todos.md · todos-v3.md · todos-v4.md · todos-v5.md · todos-v6.md · SPRINT_PROGRESS.md (Sprints 0–45)*
*Sprints 46–56 all complete as of April 2026.*
*April 25, 2026 — Reviewed go-live seeding order with user. Confirmed next actions: BUG-013 secret rotation, temp file cleanup, pytest suite, production env assertion check.*
*April 25, 2026 — BUG-S60-02: Fixed FastAPI startup crash in `bot.py` — 4 POST endpoints (`/enable`, `/disable`, `/halt`, `/resume`) used `status_code=204` which FastAPI rejects when a request/response body is present. Changed all four to `200` returning `{"ok": True}`. File: `backend/app/api/v1/endpoints/bot.py`.*
*April 25, 2026 — BUG-S60-03: Fixed Windows `UnicodeDecodeError` crash in `comments.py` — local `Limiter(key_func=get_remote_address)` instantiation bypassed the `config_filename` workaround used by the app-level limiter. Removed local Limiter; now imports shared `limiter` from `app.middleware.rate_limit`. Also fixed `DELETE /{comment_id}` using `status_code=204` with a body — changed to `200 + {"ok": True}`. Confirmed no remaining `204_NO_CONTENT` in entire `app/api/` tree. File: `backend/app/api/v1/endpoints/comments.py`. Note: must clear `__pycache__` before restarting uvicorn on Windows.*
*April 25, 2026 — BUG-S60-05: XGBoost training crash `ValueError: Invalid classes [0 2]` — multi-class objective with `num_class=3` failed when a walk-forward window had no neutral (0) class in `y_train`, causing LabelEncoder to map `{-1→0, 1→2}` skipping index 1. Fixed by switching XGBoost to binary classification (`objective="binary:logistic"`, `eval_metric="logloss"`) with target binarised as `(y > 0).astype(int)`. Applied in both walk-forward loop and final model fit. Removed unused `LabelEncoder` import. File: `backend/app/services/technical_training.py`.*
*April 26, 2026 — BUG-S60-07: Sector rotation 502 — `yf.download()` with `group_by="ticker"` deprecated in yfinance 0.2+, causing MultiIndex level ordering to flip from `(Close, Ticker)` to `(Ticker, Close)`. Fixed by removing `group_by` param and adding try/except on both `xs("Close", level=0)` and `xs("Close", level=1)` for compatibility. File: `backend/app/services/sector_service.py`.* in `seed_live_data.py` with `ChunkedIteratorResult can't be used in 'await'` — `step_sentiment()` was creating a sync `SessionLocal()` and passing it to `SentimentService` which uses async `await db.execute()`. Fixed by passing the existing `AsyncSessionLocal` session directly, removing the sync session workaround. Also consolidated both async blocks into one. File: `backend/scripts/seed_live_data.py`.*

---

## Reconciliation Fixes — April 2026

Full codebase audit performed. All items below patched in one session.

### Fixed
- [x] **scheduler.py — Syntax error** in `_make_scheduler()`: `logger.info(...)` was outside the `if` block before the `else`, causing a `SyntaxError` on import. Fixed indentation.
- [x] **scheduler.py — Duplicate `job_bot_evaluate`**: Function was defined twice (stub + full impl) and registered twice in `setup_scheduler()`. Removed the stub definition; removed the second `add_job` call. Only one registration remains at `minute="2,17,32,47"`.
- [x] **main.py — Sentry `NameError`**: `logger.info("Sentry initialised...")` was called before `logger = logging.getLogger(__name__)`. Moved Sentry block to after logger initialisation. Also replaced `__import__("os")` with clean `import os as _os`.
- [x] **main.py — `social_signals` prefix collision**: Router was mounted at `/api/v1/sentiment` (same prefix as `sentiment.router`), causing route shadowing. Changed to `/api/v1/social-signals`.
- [x] **WatchlistWidget.tsx — TS type error**: `tsc_errors_v2.txt` showed `"A_above"` (wrong case). Current code already has correct lowercase `a_above`/`b_above` — confirmed fixed in a prior session.

### Pending Manual Actions
- [ ] **BUG-013**: Run `fix_bug013.bat` from project root, then rotate ALL secrets (JWT_SECRET, FINNHUB_API_KEY, STRIPE_SECRET_KEY, REDIS_PASSWORD, etc.)
- [ ] **Delete temp files**: `SPRINT_PROGRESS_append.md`, `SPRINT_PROGRESS_header.md`, `todos-v6-patch.md`, `changed_files.txt`, `commit_files.txt`, `files_changed.txt`, `files_changed_v2.txt`, `last_commit.txt`, `tmp_latest_commit.txt` — all safe to delete.
- [ ] **Delete backend log artifacts**: `alembic_err.txt`, `alembic_out.txt`, `uvicorn.log`, `build.log` etc. in `backend/` — development noise, add to `.gitignore`.
- [ ] **Sprint 57**: Add basic test coverage for Bot, MC, Comments, Polls endpoints.

---

## Sprint 57 — Test Coverage for Sprints 47/52/56
**Completed:** April 2026

### Delivered
- [x] **`tests/api/test_bot_api.py`** — 14 tests covering GET/PATCH config, enable/disable/halt/resume, audit-log (with symbol filter), positions (empty state), and performance (mocked).
- [x] **`tests/api/test_comments_api.py`** — 13 tests covering list (empty + unknown symbol), post (success, too short/long, banned word, lowercase symbol normalisation, appears in list), delete (own, forbidden by other user, nonexistent), and react (upvote, toggle-off, invalid type).
- [x] **`tests/api/test_polls_api.py`** — 8 tests covering no-poll 404, structure, bullish vote, vote-change upsert (no duplicate), invalid option 422, nonexistent poll 404, closed poll 400, and user_vote reflected in GET /current.
- [x] **`tests/api/test_montecarlo_api.py`** — 9 tests covering asset (success, >50k paths, >3650 steps), portfolio (success, >50 assets), vol-estimate (insufficient data 404, success with seeded OHLCV rows, lowercase symbol normalisation).

### Files Created
```
backend/tests/api/test_bot_api.py
backend/tests/api/test_comments_api.py
backend/tests/api/test_polls_api.py
backend/tests/api/test_montecarlo_api.py
```

---

## Sprint 58 — Bug Fixes, Performance & README
**Completed:** April 2026

### Bugs Fixed
- [x] **`bot.py` — `NameError: datetime`** in `halt_bot()`: `datetime.now()` was called but only `timezone` was imported. Fixed by importing `datetime as _dt` alongside `timezone as tz`.
- [x] **`bot_service.py` — sync `run_asset_simulation` blocking event loop**: MC simulation (CPU-bound, ~200ms) was called directly in async context, blocking the entire event loop during every BUY evaluation. Wrapped in `loop.run_in_executor(None, run_asset_simulation, mc_params)`.
- [x] **`bot_service.py` — imports inside hot loop**: `from sqlalchemy import desc` and `import numpy as np` were inside the `evaluate_symbol()` function body (called every 15 min per user × symbol). Moved to module-level imports. Also `asyncio` added to imports.
- [x] **`bot.py` model — missing `max_sector_pct` column**: Sprint plan SQL defined `max_sector_pct FLOAT DEFAULT 0.40` but it was absent from the SQLAlchemy ORM model. Added column with `default=0.40`.

### Bugs Identified (for manual fix / next sprint)
- [ ] **`bot_configs` Alembic migration** — needs a new revision adding `max_sector_pct` column to the existing table: `alembic revision -m "add_bot_config_max_sector_pct"` then `alembic upgrade head`.
- [ ] **`BotConfigUpdate` schema** — should expose `max_sector_pct` as a PATCH-able field (range 0.10–0.60) so users can set it from the UI.
- [ ] **Audit log symbol filter bug** — `GET /bot/audit-log?symbol=NVDA` currently filters strictly by symbol but ENABLE/DISABLE/HALT/RESUME actions have `symbol=NULL`. The filter should either be symbol-only OR allow a `include_system=true` query param to also return null-symbol actions.

### Performance Improvements Identified
- [ ] **`get_positions` N+1 price fetch** — `GET /bot/positions` calls `_fetch_current_price(symbol)` serially for every open position. Should be batched with `asyncio.gather(*[_fetch_current_price(p.symbol) for p in open_positions])`.
- [ ] **`gas_precompute` batch is serial** — symbols are processed one-by-one in a `for` loop. Could run 4–6 symbols concurrently with `asyncio.gather` (with semaphore to cap DB connections).
- [ ] **`bot_audit_log` will grow unboundedly** — a SKIP is logged every 15 min per user × symbol even when nothing happens. At 10 symbols × 96 runs/day = 960 rows/user/day. Add a TTL cleanup job or only log non-SKIP/non-HOLD actions with a configurable `verbose_logging` flag on BotConfig.

### README
- [x] **Full README rewrite** — old README was titled "Yagmur Terminal" (old project name), described only the original MVP features, and was missing all 56+ sprints of new capabilities. New README covers: GAS, Signal Grade system, ML engine (XGBoost + LightGBM + Optuna), all data sources, Paper Trading Bot, MC simulation, Backtesting, Community features, full stack table, security model, running locally, and all required env keys.

---

## Performance Audit & Bug Fix Session — April 2026
**Session date:** April 21, 2026
**Scope:** Full codebase audit — performance, missing components, and bugs.

### 🔴 Critical Bugs Fixed

| # | File | Bug | Fix |
|---|------|-----|-----|
| BUG-S58-01 | `scheduler.py` | `job_bot_evaluate` defined **twice** — second definition (lines ~683–795) shadowed first, importing non-existent `get_or_create_config` causing `NameError` every bot cycle | Removed duplicate definition; only original correct implementation kept |
| BUG-S58-02 | `bot_service.py` | `run_bot_cycle` referenced in scheduler `job_bot_evaluate` but did not exist in module — every bot evaluation would `ImportError` | Added `run_bot_cycle(db)` as proper thin wrapper over `evaluate_symbol` |
| BUG-S58-03 | `layout.tsx` | App title/metadata/mobile header still showed "Yagmur Terminal" (old project name) | Changed all 3 occurrences to "Fin-Eye"; added legacy `localStorage` key migration |

### 🟠 Performance Improvements Applied

| # | File | Issue | Fix |
|---|------|-------|-----|
| PERF-01 | `bot.py` `/positions` endpoint | N+1 serial price fetches — one `_fetch_current_price()` HTTP call per open position (~5–10s for 10 positions) | Replaced with `asyncio.gather()` batch — all prices fetched concurrently |
| PERF-02 | `gas_precompute.py` `run_gas_precompute_batch()` | Symbols processed serially in a `for` loop | Replaced with `asyncio.gather()` + `Semaphore(4)` — up to 4× faster for default symbol lists |
| PERF-03 | `scheduler.py` | `job_open_insider_signals` and `job_churn_check` both fired at 09:00 UTC simultaneously — resource contention | Staggered `open_insider_signals` to 09:30 UTC |

### 🟡 Pending Manual Actions

- [x] **`bot_configs` migration** — `max_sector_pct` already present in both ORM model and `s47_001_bot_tables.py` migration. No new migration needed — confirmed by file audit.
- [x] **`BotConfigUpdate` schema** — `max_sector_pct` exposed as PATCH-able field (range 0.10–0.60) in `bot.py`. `BotConfigResponse` also updated to include it.
- [x] **`bot_audit_log` verbosity** — `verbose_logging: bool = False` added to `BotConfig` ORM model. All SKIP/HOLD log calls gated behind `config.verbose_logging`. New migration `s59_001_bot_verbose_logging.py` created. `BotConfigUpdate` + `BotConfigResponse` both expose `verbose_logging`.
- [x] **Audit log `?symbol=` filter** — `include_system: bool = True` query param added to `GET /bot/audit-log`. When `symbol` is set and `include_system=True`, returns symbol matches OR null-symbol system actions (HALT/RESUME/ENABLE/DISABLE) via `OR` clause.

### Files Modified (Session 2 — April 21, 2026)
```
backend/app/models/bot.py                              # +verbose_logging column
backend/app/services/bot_service.py                   # SKIP/HOLD logs gated by verbose_logging (4 sites)
backend/app/api/v1/endpoints/bot.py                   # +max_sector_pct, +verbose_logging in schemas; include_system param in audit-log
backend/alembic/versions/s59_001_bot_verbose_logging.py  # NEW migration
```

### Manual Step Required
```bash
cd backend
alembic upgrade head   # applies s59_001_bot_verbose_logging
```

---

## Full Performance & Correctness Audit — April 21, 2026 (Session 3)
**Scope:** Deep audit of concurrency safety, event-loop blocking, logging, DB pool, and frontend auth.

### 🔴 Critical Bugs Fixed

| # | File | Bug | Fix |
|---|------|-----|-----|
| BUG-S59-01 | `frontend/lib/api.ts` | `authHeaders()` called throughout file but **never defined** — every authenticated request (bot, billing, watchlist, referral, comments, polls) sent **no Authorization header**, returning 401/403 silently | Added `authHeaders()` definition at top of `api.ts` |
| BUG-S59-02 | `gas_precompute.py` | Concurrent `asyncio.gather` across symbols all shared **one `AsyncSession`** — SQLAlchemy async sessions are not concurrency-safe; caused `MissingGreenlet` / data corruption under load | Each symbol now gets its own `AsyncSessionLocal()` session; each commits/rolls back independently |
| BUG-S59-03 | `bot_service.py` `run_bot_cycle` | All users processed in a single session serially; one failing user blocked all others | Each user now gets own session; users processed concurrently with `Semaphore(3)` |

### 🟠 Performance Fixes Applied

| # | File | Issue | Fix |
|---|------|-------|-----|
| PERF-04 | `database.py` | Sync engine had `echo=True` — logged every SQL statement to stdout, doubling log I/O | `echo=False`; added `pool_size=10`, `max_overflow=20` to both engines |
| PERF-05 | `database.py` | No `pool_recycle` — stale connections after overnight idle cause SSL errors on first morning request | Added `pool_recycle=1800` (30 min) to async engine |
| PERF-06 | `bot.py` `_fetch_current_price` | Synchronous yfinance call directly in async context — blocked the event loop for every open position price check | Wrapped in `loop.run_in_executor(None, _sync_fetch)` |
| PERF-07 | `ml_pipeline.py` | `import math` inside `engineer_features()` — re-imported on every training run | Moved to module-level imports |
| PERF-08 | `cache_service.py` | f-string logging (`logger.error(f"...")`) — string built eagerly even when log level filters it out | Converted all 6 calls to `%s`-style lazy logging |

### Files Modified (Session 3 — April 21, 2026)
```
frontend/lib/api.ts                    # Added authHeaders() definition (CRITICAL — BUG-S59-01)
backend/app/services/gas_precompute.py # Per-symbol sessions in concurrent batch (BUG-S59-02)
backend/app/services/bot_service.py    # Per-user sessions + concurrent users in run_bot_cycle (BUG-S59-03)
backend/app/db/database.py             # echo=False, pool_size, max_overflow, pool_recycle
backend/app/api/v1/endpoints/bot.py   # _fetch_current_price wrapped in run_in_executor
backend/app/services/ml_pipeline.py   # import math moved to module level
backend/app/services/cache_service.py # f-string logging → %s-style
```

---

## Bug Audit — April 21, 2026 (Session 4)
**Scope:** Verified 4 reported issues (2–5) against actual code.

### Findings

| # | Issue | Real? | Action |
|---|-------|-------|--------|
| 2 | Sequential `run_bot_cycle` | ❌ False — already fixed in Session 3 (BUG-S59-03) | None |
| 3 | Memory-intensive `get_bot_performance` | ✅ Real | Fixed — replaced `.scalars().all()` row fetch with `func.sum/count/max/min/avg` aggregate queries (3 DB queries, O(1) memory) |
| 4 | Missing sector exposure gate | ✅ Real | Gate added in `evaluate_symbol` BUY path; silently no-ops until `sector` field added to `GasSnapshot` — see follow-up below |
| 5 | Audit log hides system actions on symbol filter | ❌ False — already fixed in Session 3 (`include_system=True` + `or_` clause) | None |

### Follow-up: GasSnapshot needs `sector` column
- `BotConfig.max_sector_pct` gate is implemented but `GasSnapshot` has no `sector` field
- Fix: add `sector = Column(String(60), nullable=True)` to `GasSnapshot`, populate in `gas_precompute.py` from yfinance `.info["sector"]`
- Status: **In progress (Session 4)**

### Files Modified (Session 4 — April 21, 2026)
```
backend/app/services/bot_service.py      # Issue 3: aggregate queries in get_bot_performance; Issue 4: sector gate in evaluate_symbol BUY path
backend/app/models/gas_snapshot.py       # Added sector = Column(String(60), nullable=True)
backend/app/crud/gas_snapshot.py         # upsert_snapshot: added sector param + persists it
backend/app/services/gas_precompute.py   # _fetch_sector_sync + _get_sector helpers; fetches sector concurrently; passes to upsert_snapshot
backend/alembic/versions/s60_001_gas_snapshot_sector.py  # Migration: ADD COLUMN sector VARCHAR(60) to gas_snapshots
```

### Manual Step Required
```bash
cd backend
alembic upgrade head   # applies s60_001_gas_snapshot_sector
```

---

## Bug & Cleanup Session — April 21, 2026 (Session 5)
**Scope:** 5 follow-up issues from Session 4 + fresh audit of main.py and scheduler.

### Findings

| # | Issue | Real? | Fix |
|---|-------|-------|-----|
| 1 | `max_sector_pct` migration | ❌ False — already in `s47_001_bot_tables.py` | None |
| 2 | `GasSnapshot.to_dict()` missing `sector` | ✅ Real | Added `"sector": self.sector` |
| 3 | Sector fetch on every precompute run | ✅ Real | Skip yfinance call if snapshot already has sector; only fetches for new symbols |
| 4 | Test mock stale field names | ✅ Real | Fixed `win_rate`→`win_rate_pct`, `best/worst_trade_pct`→`best/worst_trade_usd`, added `wins`/`losses`/`avg_hold_hours` |
| 5 | Frontend missing `max_sector_pct` | ✅ Real | Added slider (10–60%), wired to `updateBotConfig`, shown in summary row; fixed `win_rate`→`win_rate_pct` display; updated `BotPerformanceDto` TS type |

### Additional Issues Found & Fixed

| # | Issue | Fix |
|---|-------|-----|
| A | `main.py` double R2 sync — `sync_models_from_r2` called once blocking then again in background task | Removed blocking call; only background task `_sync_r2_models_bg` runs (at +5s); scheduler start moved back to correct position |
| B | `bot_audit_log` grows unboundedly — no TTL cleanup job | Added `job_bot_audit_log_cleanup`: deletes rows > 90 days old; runs weekly Sunday 03:00 UTC |
| C | `job_churn_check` and `job_onboarding_day3` both at `hour=9, minute=0` | Staggered `churn_check` to 09:15 UTC |

### Files Modified (Session 5 — April 21, 2026)
```
backend/app/models/gas_snapshot.py       # to_dict(): added sector field
backend/app/services/gas_precompute.py   # skip sector yfinance fetch if already stored
backend/tests/api/test_bot_api.py        # fixed mock shape to match new get_bot_performance response
frontend/app/bot/paper/page.tsx          # max_sector_pct slider + summary row + win_rate_pct fix
frontend/lib/api.ts                      # BotPerformanceDto: win_rate_pct, wins, losses, removed stale fields
backend/app/main.py                      # removed duplicate R2 sync; restored scheduler.start(); clean background tasks
backend/app/services/scheduler.py       # job_bot_audit_log_cleanup added; churn_check offset to 09:15
```

---

## Manual Trigger Audit — April 21, 2026 (Session 6)
**Scope:** Verified all manual trigger endpoints and admin UI controls.

### Bugs Found & Fixed

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1 | `data.py` | `POST /data/fetch/ohlcv`, `/fetch/macro`, `/fetch/news` had **no auth** — open to unauthenticated users | Added `dependencies=[Depends(require_admin)]` to all three |
| 2 | `ops.py` `backup-now` | Used `asyncio.create_task()` inside request context — task can be silently killed if event loop shuts down before it completes | Replaced with `BackgroundTasks.add_task()` (FastAPI-managed, request lifecycle safe) |
| 3 | `admin_gas.py` `POST /precompute` | No concurrency guard — double-clicking "Run All Symbols" spawned two concurrent full precompute batches, doubling DB load | Added `_batch_running` module-level flag; returns `{"status": "already_running"}` on second call |
| 4 | `admin/gas/page.tsx` | `batchStatus` never reset to `"idle"` — "Run All Symbols" button stayed stuck in "Running…" forever after triggering | Button resets to idle after 60s (with refresh) or immediately on `already_running`; errors auto-reset after 5s |

### Files Modified (Session 6 — April 21, 2026)
```
backend/app/api/v1/data.py                        # require_admin on all 3 fetch trigger endpoints
backend/app/api/v1/endpoints/ops.py               # backup-now: asyncio.create_task → BackgroundTasks; added BackgroundTasks import
backend/app/api/v1/endpoints/admin_gas.py         # _batch_running lock; already_running response
frontend/app/admin/gas/page.tsx                   # button resets after 60s; already_running handled; error auto-reset
```
Email: admin@yagmurterminal.com
Password: admin