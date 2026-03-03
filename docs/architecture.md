# Fin-Eye – Architecture Overview

> **Date:** 2026-03-03

---

## System Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 14)                     │
│  /             /explore/[sym]  /macro  /news-sentiment       │
│  Dashboard     DeepExplore     Macro   Sentiment             │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP fetch / SWR
┌──────────────────────▼──────────────────────────────────────┐
│                   BACKEND (FastAPI)                          │
│  /api/v1/macro   /explore   /technical   /sentiment          │
│  MacroOrchestrator  ExploreService  TechnicalConsensus       │
└───────────┬──────────────────────┬──────────────────────────┘
            │ SQLAlchemy ORM       │ Redis (cache)
┌───────────▼──────────┐  ┌───────▼───────────────────────── ┐
│  PostgreSQL Database  │  │  Redis Cache (TTL-based)          │
│  StockOHLCV           │  │  macro:latest  sentiment:{sym}    │
│  MacroIndicator        │  │  technical:{sym}:{tf}            │
│  NewsArticle           │  └──────────────────────────────────┘
│  SentimentAggregate    │
└───────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────── ┐
│  ML Layer (model_store/)                                      │
│  DbFeatureBuilder → technical_training → ModelArtifactStore  │
│  JsonlFileModelRegistry  →  technical_consensus              │
└───────────────────────────────────────────────────────────── ┘
            │
┌───────────▼──────────────────────────────────────────────── ┐
│  External Data Sources                                        │
│  Yahoo Finance (OHLCV)  FRED (Macro)  Finnhub (News)         │
└───────────────────────────────────────────────────────────── ┘
```

---

## Backend Module Map

```
backend/app/
├── config.py                    Pydantic settings (from .env)
├── main.py                      FastAPI app, lifespan, routers
├── db/
│   ├── database.py              SQLAlchemy engine + session
│   └── redis_client.py          Async Redis connection pool
├── models/                      SQLAlchemy ORM models
│   ├── market.py                StockOHLCV
│   ├── macro.py                 MacroIndicator
│   └── sentiment.py             NewsArticle, SentimentAggregate
├── schemas/
│   └── data_models.py           Pydantic request/response models
├── crud/
│   └── macro.py                 DB CRUD helpers for macro
├── services/
│   ├── market_data.py           OHLCVFetcher (Yahoo Finance)
│   ├── macro_data.py            MacroFetcher (FRED)
│   ├── news_data.py             NewsFetcher (Finnhub)
│   ├── sentiment_service.py     FinBERT sentiment aggregator
│   ├── cache_service.py         Generic Redis cache wrapper
│   ├── feature_builder.py       DbFeatureBuilder (OHLCV+Macro+Sentiment → DataFrame)
│   ├── technical_models.py      Enums, dataclasses, walk-forward helpers
│   ├── technical_training.py    Logistic + XGBoost training orchestration
│   ├── technical_consensus.py   Multi-timeframe consensus + 0-100 score
│   ├── model_registry.py        InMemory + JSONL model metadata registry
│   ├── model_artifacts.py       joblib / XGBoost artifact save+load
│   └── macro_scoring.py         compute_macro_score() shared heuristic
└── api/v1/endpoints/
    ├── macro.py                 GET /macro/latest, POST /macro/refresh
    ├── sentiment.py             GET /sentiment/{sym}/timeseries, /sources
    ├── technical.py             GET /technical/{sym}/latest
    └── exploration.py           GET /explore/{sym}/deep, /consensus-history  [NEW]
```

---

## Frontend Module Map

```
frontend/
├── app/
│   ├── layout.tsx               Global nav bar + font/theme setup
│   ├── page.tsx                 Dashboard (GAS + regime + timeframe grid)
│   ├── explore/[symbol]/
│   │   └── page.tsx             Deep Exploration (chart + features + consensus)
│   ├── macro/
│   │   └── page.tsx             Macro View
│   └── news-sentiment/
│       └── page.tsx             News & Sentiment View
├── lib/
│   └── api.ts                   All typed fetch functions → backend
└── components/
    ├── MarketWeatherWidget.tsx   GAS display
    ├── RegimeWidget.tsx          Regime display
    ├── TimeframeGrid.tsx         5-column consensus tiles
    ├── SentimentChart.tsx        30-day line chart
    ├── ArticleList.tsx           Scored headlines
    └── SourceBreakdownTable.tsx  Per-outlet sentiment table
```

---

## Data Flow: Exploration Page

```
User visits /explore/AAPL
     │
     ▼
page.tsx  calls  fetchExplorationDeep("AAPL")  [lib/api.ts]
     │
     ▼
GET /api/v1/explore/AAPL/deep
     │
     ├── DbFeatureBuilder.build_features("AAPL", "1d", start, end)
     │     ├── Query StockOHLCV
     │     ├── Compute RSI-14, MACD, Bollinger Bands, Returns, Vol
     │     ├── Join MacroIndicator (VIX, yield_spread, macro_score)
     │     └── Join SentimentAggregate
     │
     └── Returns unified JSON → rendered in OHLCVChart + FeaturePanel + ConsensusBox
```
