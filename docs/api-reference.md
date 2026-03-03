# Fin-Eye – API Reference

> **Base URL:** `http://localhost:8000/api/v1`  
> **Date:** 2026-03-03  
> All endpoints return JSON. Authentication is not yet enforced (deferred to CORE-AUTH-01).

---

## Macro

### `GET /macro/latest`
Returns latest values for all 5 macro indicators plus the composite Macro Score.

**Response:**
```json
{
  "indicators": [
    { "name": "fed_funds_rate", "value": 5.33, "interpretation": "Restrictive – Fed is tightening" },
    { "name": "unemployment_rate", "value": 3.9, "interpretation": "Near full employment" },
    { "name": "cpi_yoy", "value": 3.1, "interpretation": "Inflation above target" },
    { "name": "yield_spread_10y_2y", "value": -0.45, "interpretation": "Inverted – recession risk" },
    { "name": "vix", "value": 16.2, "interpretation": "Moderate fear" }
  ],
  "macro_score": { "value": 48, "label": "Neutral" }
}
```

### `POST /macro/refresh`
Triggers a fresh pull from FRED and Finnhub APIs. Returns updated indicator list.

---

## Sentiment

### `GET /sentiment/{symbol}/timeseries`
Returns 30-day daily sentiment time-series, rolling averages, and recent articles.

**Path params:** `symbol` – ticker (e.g., `AAPL`)

**Response:**
```json
{
  "symbol": "AAPL",
  "timeseries": [{ "date": "2026-02-01", "score": 0.23 }],
  "averages": { "1d": 0.31, "7d": 0.18, "30d": 0.12 },
  "articles": [{ "title": "...", "source": "Reuters", "score": 0.4, "date": "2026-03-03" }]
}
```

### `GET /sentiment/{symbol}/sources`
Returns per-outlet sentiment counts over the last N days (default 30).

**Response:**
```json
{
  "symbol": "AAPL",
  "breakdown": [
    { "source": "Reuters", "positive": 12, "negative": 3, "neutral": 5 }
  ]
}
```

---

## Technical / ML

### `GET /technical/{symbol}/latest`
Returns the multi-timeframe consensus and 0–100 Technical Confidence Score.

**Response:**
```json
{
  "symbol": "AAPL",
  "consensus_score": 68,
  "consensus_direction": 1,
  "timeframes": [
    { "timeframe": "1d", "direction": 1, "confidence": 0.72, "sharpe": 1.4 },
    { "timeframe": "1w", "direction": 1, "confidence": 0.65, "sharpe": 1.1 }
  ]
}
```

---

## Explanation (MVP-EXPL-01 / 02)

### `GET /explanation/{symbol}/summary`
Derives the "Why is this moving?" explanation (EXPL-01) and conflict detector (EXPL-02) from pre-computed layer scores passed as query params.

**Query params:**
- `tech_score` (float)
- `sent_30d` (float, optional)
- `macro_score` (float)
- `macro_label` (string)
- `gas_score` (float)
- `tech_signals` (string, JSON-encoded list of timeframe signals)

**Response:**
```json
{
  "symbol": "AAPL",
  "gas_score": 68.5,
  "gas_label": "Mild Support",
  "why_moving": [
    "📈 Technical momentum is bullish — 4 of 5 timeframes bullish, 1 bearish (confidence score: 72/100).",
    "📰 News sentiment over the past 30 days is strongly positive (score: +0.45 on a −1 to +1 scale).",
    "🌐 Macro backdrop is 'Neutral' (score: 48/100). Macro conditions are broadly neutral."
  ],
  "disclaimer": "This is educational analysis, not investment advice...",
  "has_conflict": false,
  "conflicts": [],
  "conflict_summary": "No major conflicts detected — layers are broadly aligned."
}
```

---

## Backtesting  ← PLANNED (MVP-BACK-01)

### `POST /backtest/run`
Submit a backtest configuration. Returns a job ID.

### `GET /backtest/{id}/results`
Poll for results. Returns equity curve, metrics, and trade log.

---

## Hedging  ← PLANNED (MVP-HEDGE-01)

### `GET /hedge/{symbol}/correlation`
Returns correlation matrix vs. SPY, QQQ, GLD, TLT.

### `GET /hedge/{symbol}/ratio`
Returns beta-adjusted hedge ratio suggestion.
