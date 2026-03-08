#!/usr/bin/env python3
"""
scripts/seed_all_data.py
════════════════════════════════════════════════════════════════════════════════
Fin-Eye — Full Manual Data Seeder / Test Data Generator

PURPOSE
───────
Run this script to populate ALL dynamic data sources with realistic, live-
fetched data so the app looks fully operational with no static/placeholder
content. Useful for:
  • Local development first-boot
  • Staging environment setup
  • Demo/review sessions
  • After wiping the DB to start fresh

WHAT IT SEEDS
─────────────
  1.  Database tables (via init_db)
  2.  Admin user
  3.  Demo user (free tier)
  4.  Pro demo user
  5.  OHLCV bars — daily + weekly for all default symbols
  6.  Intraday bars (1h) for default symbols
  7.  News articles (Finnhub, last 7 days)
  8.  Sentiment aggregates (FinBERT processed)
  9.  Macro indicators (FRED)
  10. GAS snapshots for all symbols (pre-compute batch)
  11. Watchlist items for demo user
  12. Portfolio positions for demo user
  13. Custom indicators (example formulas)
  14. Sample blog/learn posts
  15. Showcase products (digital product catalog)
  16. Alerts (sample price + GAS alerts)
  17. Saved backtest strategies
  18. Email preferences (opted-in)
  19. Legal consents
  20. Analytics events (synthetic activation funnel)
  21. Redis cache warm (GAS + macro)

USAGE
─────
  cd backend
  python scripts/seed_all_data.py [--symbols AAPL,MSFT] [--skip-ml] [--fast]

FLAGS
─────
  --symbols   Comma-separated list of tickers to seed (default: all)
  --skip-ml   Skip ML training and GAS pre-compute (faster, scores will be 50)
  --fast      Only seed critical path data (users, OHLCV, macro, GAS)
  --reset     Drop and recreate all tables before seeding (DESTRUCTIVE)
  --demo-only Only seed demo users + watchlists (no market data pipeline)

NOTES
─────
  • Requires a running PostgreSQL and Redis (set DATABASE_URL and REDIS_URL)
  • Requires API keys in .env: FRED_API_KEY, FINNHUB_API_KEY (optional)
  • yfinance data is free and requires no key
  • Script is idempotent — re-running will upsert, not duplicate

════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Bootstrap path so we can import app modules ──────────────────────────────
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.db.database import init_db, AsyncSessionLocal
from app.core.security import hash_password

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("seeder")

# ── Default symbols ───────────────────────────────────────────────────────────
DEFAULT_SYMBOLS = settings.ohlcv_symbols_default or [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "SPY",  "QQQ",  "NVDA",  "META", "JPM",
    "GLD",  "TLT",  "BTC-USD", "ETH-USD",
    "GC=F", "CL=F",
]

# ── Demo users ────────────────────────────────────────────────────────────────
ADMIN_EMAIL    = "admin@fin-eye.com"
ADMIN_PASSWORD = "AdminFinEye2024!"
DEMO_EMAIL     = "demo@fin-eye.com"
DEMO_PASSWORD  = "DemoFinEye2024!"
PRO_EMAIL      = "pro@fin-eye.com"
PRO_PASSWORD   = "ProFinEye2024!"


# ════════════════════════════════════════════════════════════════════════════
# STEP 1 — Database init
# ════════════════════════════════════════════════════════════════════════════

def step_init_db() -> None:
    logger.info("▶ Step 1: Initializing database tables...")
    # Import models here to ensure they are registered with Base.metadata before init_db()
    import app.models
    init_db()
    logger.info("  ✓ All tables created/verified")


# ════════════════════════════════════════════════════════════════════════════
# STEP 2 — Users
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_users(db) -> dict:
    """Create admin, demo, and pro users. Returns {email: User} map."""
    from sqlalchemy import select
    from app.models.user import User
    from app.models.email_preference import EmailPreference

    users = {}
    for email, password, name, tier, is_admin in [
        (ADMIN_EMAIL, ADMIN_PASSWORD, "Admin User", "institutional", True),
        (DEMO_EMAIL,  DEMO_PASSWORD,  "Demo User",  "free",          False),
        (PRO_EMAIL,   PRO_PASSWORD,   "Pro User",   "pro",           False),
    ]:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                name=name,
                subscription_tier=tier,
                is_admin=is_admin,
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.flush()
            # Email preferences
            pref = EmailPreference(
                user_id=user.id,
                marketing_opted_in=True,
                digest_opted_in=True,
                unsubscribe_token=str(uuid.uuid4()),
                onboarding_step=0,
            )
            db.add(pref)
            logger.info("  ✓ Created user: %s (%s)", email, tier)
        else:
            logger.info("  ↩ User exists: %s", email)
        users[email] = user

    await db.commit()
    return users


# ════════════════════════════════════════════════════════════════════════════
# STEP 3 — OHLCV bars
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_ohlcv(db, symbols: list[str], fast: bool = False) -> None:
    logger.info("▶ Step 3: Seeding OHLCV bars for %d symbols...", len(symbols))
    try:
        from app.services.ohlcv_fetcher import OHLCVFetcher
        fetcher = OHLCVFetcher()
        results = await fetcher.fetch_and_store_daily(db)
        logger.info("  ✓ Daily OHLCV: %s", results)
        if not fast:
            r1h = await fetcher.fetch_and_store_intraday(db, interval="1h")
            logger.info("  ✓ Intraday 1h: %s", r1h)
        await db.commit()
    except Exception as exc:
        logger.warning("  ⚠ OHLCV seed failed (non-fatal): %s", exc)


# ════════════════════════════════════════════════════════════════════════════
# STEP 4 — News articles
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_news(db, symbols: list[str]) -> None:
    logger.info("▶ Step 4: Fetching news articles...")
    try:
        from app.services.news_data import NewsFetcher
        fetcher = NewsFetcher()
        results = await fetcher.fetch_and_store(db, lookback_days=7)
        await db.commit()
        logger.info("  ✓ News: %s", results)
    except Exception as exc:
        logger.warning("  ⚠ News seed failed (non-fatal): %s", exc)


# ════════════════════════════════════════════════════════════════════════════
# STEP 5 — Macro indicators (FRED)
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_macro(db) -> None:
    logger.info("▶ Step 5: Refreshing macro indicators (FRED)...")
    try:
        from app.services.macro_orchestrator import refresh_all_macro_indicators
        await refresh_all_macro_indicators(db)
        await db.commit()
        logger.info("  ✓ Macro indicators refreshed")
    except Exception as exc:
        logger.warning("  ⚠ Macro seed failed (non-fatal, FRED key may be missing): %s", exc)


# ════════════════════════════════════════════════════════════════════════════
# STEP 6 — GAS pre-compute (ML training + snapshot)
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_gas(db, symbols: list[str], skip_ml: bool) -> None:
    logger.info("▶ Step 6: Running GAS pre-compute for %d symbols...", len(symbols))
    if skip_ml:
        logger.info("  ↩ --skip-ml flag set, using neutral scores (50.0)")
    try:
        from app.services.gas_precompute import run_gas_precompute_batch
        summary = await run_gas_precompute_batch(db, symbols=symbols if symbols != DEFAULT_SYMBOLS else None)
        await db.commit()
        logger.info(
            "  ✓ GAS: %d/%d succeeded, macro_score=%.1f, %.0fms",
            summary["symbols_succeeded"], summary["symbols_attempted"],
            summary["macro_score_shared"], summary["elapsed_ms"],
        )
    except Exception as exc:
        logger.warning("  ⚠ GAS pre-compute failed (non-fatal): %s", exc)


# ════════════════════════════════════════════════════════════════════════════
# STEP 7 — Watchlist
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_watchlist(db, users: dict) -> None:
    logger.info("▶ Step 7: Seeding watchlist items...")
    from sqlalchemy import select
    from app.models.watchlist import WatchlistItem

    demo_user = users.get(DEMO_EMAIL)
    if not demo_user:
        return

    watchlist_symbols = ["AAPL", "MSFT", "TSLA", "SPY", "BTC-USD", "GLD"]
    for sym in watchlist_symbols:
        exists = await db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == demo_user.id,
                WatchlistItem.symbol == sym,
            )
        )
        if not exists.scalar_one_or_none():
            db.add(WatchlistItem(user_id=demo_user.id, symbol=sym))
    await db.commit()
    logger.info("  ✓ Watchlist seeded (%d symbols)", len(watchlist_symbols))


# ════════════════════════════════════════════════════════════════════════════
# STEP 8 — Portfolio positions
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_portfolio(db, users: dict) -> None:
    logger.info("▶ Step 8: Seeding demo portfolio...")
    from sqlalchemy import select
    from app.models.portfolio import Portfolio, PortfolioPosition

    demo_user = users.get(DEMO_EMAIL)
    if not demo_user:
        return

    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == demo_user.id, Portfolio.name == "Demo Portfolio")
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        portfolio = Portfolio(user_id=demo_user.id, name="Demo Portfolio", description="Seeded demo portfolio")
        db.add(portfolio)
        await db.flush()

        positions = [
            ("AAPL",  40, 185.50,  "USD"),
            ("MSFT",  20, 420.00,  "USD"),
            ("GOOGL", 10, 175.00,  "USD"),
            ("SPY",   15, 580.00,  "USD"),
            ("GLD",   30, 195.00,  "USD"),
            ("BTC-USD", 0.5, 95000.0, "USD"),
        ]
        for sym, qty, price, currency in positions:
            db.add(PortfolioPosition(
                portfolio_id=portfolio.id,
                symbol=sym,
                quantity=qty,
                average_cost=price,
                currency=currency,
            ))
        await db.commit()
        logger.info("  ✓ Portfolio seeded with %d positions", len(positions))
    else:
        logger.info("  ↩ Portfolio already exists")


# ════════════════════════════════════════════════════════════════════════════
# STEP 9 — Custom indicators
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_indicators(db, users: dict) -> None:
    logger.info("▶ Step 9: Seeding custom indicator examples...")
    from sqlalchemy import select
    from app.models.custom_indicator import CustomIndicator

    demo_user = users.get(DEMO_EMAIL)
    if not demo_user:
        return

    examples = [
        {
            "name": "RSI Oversold Signal",
            "description": "Fires when RSI(14) drops below 30 — classic oversold condition",
            "formula": {
                "type": "binop", "op": "<",
                "left": {"type": "indicator", "fn": "RSI", "params": {"period": 14}},
                "right": {"type": "number", "value": 30},
            },
        },
        {
            "name": "Golden Cross",
            "description": "SMA50 crosses above SMA200 — bullish long-term signal",
            "formula": {
                "type": "cross", "direction": "above",
                "fast": {"type": "indicator", "fn": "SMA", "params": {"period": 50}},
                "slow": {"type": "indicator", "fn": "SMA", "params": {"period": 200}},
            },
        },
        {
            "name": "MACD Momentum",
            "description": "MACD line value — positive = bullish momentum",
            "formula": {"type": "indicator", "fn": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "output": "macd"},
        },
        {
            "name": "Bollinger Squeeze",
            "description": "BB width < 0.05 indicates low volatility / potential breakout",
            "formula": {
                "type": "binop", "op": "<",
                "left": {"type": "indicator", "fn": "BB", "params": {"period": 20, "std": 2.0}, "output": "width"},
                "right": {"type": "number", "value": 0.05},
            },
        },
        {
            "name": "RSI − 50 Centred",
            "description": "RSI centred around zero — positive = above midpoint, negative = below",
            "formula": {
                "type": "binop", "op": "-",
                "left": {"type": "indicator", "fn": "RSI", "params": {"period": 14}},
                "right": {"type": "number", "value": 50},
            },
        },
    ]

    for example in examples:
        exists = await db.execute(
            select(CustomIndicator).where(
                CustomIndicator.user_id == demo_user.id,
                CustomIndicator.name == example["name"],
            )
        )
        if not exists.scalar_one_or_none():
            db.add(CustomIndicator(
                user_id=demo_user.id,
                name=example["name"],
                description=example["description"],
                formula=example["formula"],
            ))
    await db.commit()
    logger.info("  ✓ %d custom indicators seeded", len(examples))


# ════════════════════════════════════════════════════════════════════════════
# STEP 10 — Blog / Learn posts
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_blog(db) -> None:
    logger.info("▶ Step 10: Seeding learn/blog posts...")
    from sqlalchemy import select
    from app.models.blog import BlogPost

    now = datetime.now(timezone.utc)
    posts = [
        {
            "slug": "what-is-the-gas-score",
            "title": "What is the Global Alignment Score (GAS)?",
            "category": "Education",
            "read_time": "5 min read",
            "author": "Fin-Eye Team",
            "summary": "A deep-dive into the GAS formula: how technical ML signals, macro data, and sentiment combine into a single 0–100 score.",
            "content_md": "## What is the GAS Score?\n\nThe **Global Alignment Score (GAS)** is Fin-Eye's core composite metric...\n\n[Full article content goes here]",
            "status": "published",
            "published_at": now,
        },
        {
            "slug": "reading-the-yield-curve",
            "title": "Reading the Yield Curve: What Inverted Means for Markets",
            "category": "Macro",
            "read_time": "5 min read",
            "author": "Fin-Eye Team",
            "summary": "The 10Y-2Y spread has predicted every US recession since 1980. Here's how to read it on Fin-Eye.",
            "content_md": "## The Yield Curve Explained\n\nWhen short-term rates exceed long-term rates...",
            "status": "published",
            "published_at": now,
        },
        {
            "slug": "rsi-divergence-guide",
            "title": "RSI Divergence: Spotting Trend Exhaustion Early",
            "category": "Technical",
            "read_time": "5 min read",
            "author": "Fin-Eye Team",
            "summary": "Bullish and bearish RSI divergence explained with real chart examples. One of the most reliable signals in technical analysis.",
            "content_md": "## RSI Divergence\n\nDivergence occurs when price moves in the opposite direction of the RSI indicator...",
            "status": "published",
            "published_at": now,
        },
        {
            "slug": "digital-nomad-financial-guide",
            "title": "The Digital Nomad's Financial Playbook",
            "category": "Lifestyle",
            "read_time": "5 min read",
            "author": "Fin-Eye Team",
            "summary": "Tax residency, banking, investment structures, and managing currency risk as a location-independent professional.",
            "content_md": "## Financial Planning for Digital Nomads\n\nMoving between countries creates unique financial challenges...",
            "status": "published",
            "published_at": now,
        },
        {
            "slug": "tax-efficient-investing-structures",
            "title": "Tax-Efficient Investment Structures: LLC, Cyprus, UAE & Beyond",
            "category": "Tax & Legal",
            "read_time": "5 min read",
            "author": "Fin-Eye Team",
            "summary": "An overview of legal structures used by international investors — from US LLCs to Cyprus holding companies and UAE freezone entities.",
            "content_md": "## Legal Investment Structures\n\nThis article is for informational purposes only and does not constitute legal or tax advice...",
            "status": "published",
            "published_at": now,
        },
        {
            "slug": "2008-financial-crisis-case-study",
            "title": "Case Study: The 2008 Financial Crisis Through the GAS Lens",
            "category": "Case Studies",
            "read_time": "5 min read",
            "author": "Fin-Eye Team",
            "summary": "What would the GAS score have looked like in 2007-2008? A retrospective analysis using macro, sentiment, and technical signals.",
            "content_md": "## 2008: A Retrospective\n\nThe Global Financial Crisis was preceded by months of macro deterioration...",
            "status": "published",
            "published_at": now,
        },
    ]

    for post_data in posts:
        exists = await db.execute(select(BlogPost).where(BlogPost.slug == post_data["slug"]))
        if not exists.scalar_one_or_none():
            db.add(BlogPost(**post_data))
    await db.commit()
    logger.info("  ✓ %d blog posts seeded", len(posts))


# ════════════════════════════════════════════════════════════════════════════
# STEP 11 — Showcase / Digital products
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_showcase(db) -> None:
    logger.info("▶ Step 11: Seeding digital product showcase...")
    from sqlalchemy import select
    from app.models.showcase import ShowcaseProduct

    products = [
        {
            "title": "Investment Portfolio Tracker (Excel)",
            "tagline": "Track stocks, ETFs & crypto in one workbook",
            "description": "A comprehensive Excel workbook for tracking stocks, ETFs, and crypto. Includes live data connections, P&L tracking, dividend calendar, and portfolio heat map.",
            "features": ["P&L tracking", "Dividend calendar", "Portfolio heat map", "Live data connections"],
            "category": "Excel Templates",
            "price_label": "€12.99",
            "external_url": "https://app.lemonsqueezy.com/checkout/buy/investment-tracker",
            "is_active": True,
            "sort_order": 10,
        },
        {
            "title": "Retirement Planning Calculator (Excel)",
            "tagline": "Monte Carlo retirement projections in Excel",
            "description": "Model your retirement with Monte Carlo simulation, safe withdrawal rate analysis, Social Security/pension integration, and 30-year projection charts.",
            "features": ["Monte Carlo simulation", "Safe withdrawal rate", "30-year projections", "Pension integration"],
            "category": "Excel Templates",
            "price_label": "€14.99",
            "external_url": "https://app.lemonsqueezy.com/checkout/buy/retirement-planner",
            "is_active": True,
            "sort_order": 20,
        },
        {
            "title": "Household Budget & Expense Tracker (Excel)",
            "tagline": "Beautiful monthly budget with charts",
            "description": "Beautiful monthly budget tracker with category pie charts, savings rate tracking, bill due-date reminders, and year-over-year comparison.",
            "features": ["Category pie charts", "Savings rate tracking", "Bill reminders", "Year-over-year comparison"],
            "category": "Excel Templates",
            "price_label": "€7.99",
            "external_url": "https://app.lemonsqueezy.com/checkout/buy/household-budget",
            "is_active": True,
            "sort_order": 30,
        },
        {
            "title": "Teen Financial Planner (Google Sheets)",
            "tagline": "Fun financial tracker for teenagers",
            "description": "A fun, emoji-friendly financial tracker designed for teenagers. Track allowance, savings goals, spending categories, and learn about compound interest.",
            "features": ["Allowance tracking", "Savings goals", "Compound interest calculator", "Mobile-friendly"],
            "category": "Google Sheets",
            "price_label": "€4.99",
            "external_url": "https://app.lemonsqueezy.com/checkout/buy/teen-planner",
            "is_active": True,
            "sort_order": 40,
        },
        {
            "title": "Dividend Income Tracker (Excel)",
            "tagline": "Track dividends, ex-dates & projected income",
            "description": "Track dividend payments, ex-dates, yield-on-cost, and projected annual income. Includes dividend calendar heatmap and DRIP calculator.",
            "features": ["Dividend calendar heatmap", "Yield-on-cost tracking", "DRIP calculator", "Projected annual income"],
            "category": "Excel Templates",
            "price_label": "€9.99",
            "external_url": "https://app.lemonsqueezy.com/checkout/buy/dividend-tracker",
            "is_active": True,
            "sort_order": 50,
        },
        {
            "title": "Options P&L Tracker (Excel)",
            "tagline": "Full options trade log with Greeks & P&L",
            "description": "Track your options trades with automatic P&L, Greeks tracking, win rate analysis, and max loss/profit scenarios. Includes covered calls and cash-secured puts workflow.",
            "features": ["Auto P&L calculation", "Greeks tracking", "Win rate analysis", "Covered calls workflow"],
            "category": "Excel Templates",
            "price_label": "€19.99",
            "external_url": "https://app.lemonsqueezy.com/checkout/buy/options-tracker",
            "is_active": True,
            "sort_order": 60,
        },
    ]

    for p in products:
        exists = await db.execute(select(ShowcaseProduct).where(ShowcaseProduct.title == p["title"]))
        if not exists.scalar_one_or_none():
            db.add(ShowcaseProduct(**p))
    await db.commit()
    logger.info("  ✓ %d showcase products seeded", len(products))


# ════════════════════════════════════════════════════════════════════════════
# STEP 12 — Alerts
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_alerts(db, users: dict) -> None:
    logger.info("▶ Step 12: Seeding sample alerts...")
    from sqlalchemy import select
    from app.models.alert import Alert

    demo_user = users.get(DEMO_EMAIL)
    if not demo_user:
        return

    count_result = await db.execute(
        select(Alert).where(Alert.user_id == demo_user.id)
    )
    if count_result.scalars().all():
        logger.info("  ↩ Alerts already exist")
        return

    sample_alerts = [
        {"symbol": "AAPL",    "alert_type": "price_above",  "threshold": 220.00, "delivery_channel": "in_app"},
        {"symbol": "TSLA",    "alert_type": "price_below",  "threshold": 200.00, "delivery_channel": "email"},
        {"symbol": "SPY",     "alert_type": "gas_below",    "threshold": 40.0,   "delivery_channel": "email"},
        {"symbol": "BTC-USD", "alert_type": "price_above",  "threshold": 110000, "delivery_channel": "in_app"},
        {"symbol": "NVDA",    "alert_type": "gas_above",    "threshold": 75.0,   "delivery_channel": "in_app"},
    ]
    for a in sample_alerts:
        db.add(Alert(user_id=demo_user.id, **a))
    await db.commit()
    logger.info("  ✓ %d alerts seeded", len(sample_alerts))


# ════════════════════════════════════════════════════════════════════════════
# STEP 13 — Saved strategies
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_strategies(db, users: dict) -> None:
    logger.info("▶ Step 13: Seeding saved strategies...")
    from sqlalchemy import select, text

    demo_user = users.get(DEMO_EMAIL)
    if not demo_user:
        return

    try:
        from app.models.strategy import SavedStrategy
        exists = await db.execute(select(SavedStrategy).where(SavedStrategy.user_id == demo_user.id))
        if exists.scalars().all():
            logger.info("  ↩ Strategies already exist")
            return

        strategies = [
            {
                "name": "RSI Momentum",
                "description": "Buy when RSI crosses above 50, sell below 40. Medium-term momentum strategy.",
                "request_snapshot": {"symbol": "AAPL", "strategy": "rsi_momentum", "params": {"rsi_period": 14, "entry_threshold": 50, "exit_threshold": 40}, "lookback": "1y", "capital": 10000},
                "is_public": True,
                "sharpe_ratio": 1.42,
                "total_return_pct": 23.0,
                "annualized_return_pct": 18.5,
                "max_drawdown_pct": -12.3,
                "win_rate_pct": 58.0,
                "total_trades": 24,
            },
            {
                "name": "Golden Cross SPY",
                "description": "Classic SMA50/200 crossover on SPY. Long-only, fully invested or cash.",
                "request_snapshot": {"symbol": "SPY", "strategy": "sma_crossover", "params": {"fast_sma": 50, "slow_sma": 200}, "lookback": "5y", "capital": 10000},
                "is_public": True,
                "sharpe_ratio": 0.89,
                "total_return_pct": 67.0,
                "annualized_return_pct": 11.2,
                "max_drawdown_pct": -18.7,
                "win_rate_pct": 52.0,
                "total_trades": 12,
            },
        ]
        for s in strategies:
            db.add(SavedStrategy(user_id=demo_user.id, **s))
        await db.commit()
        logger.info("  ✓ %d strategies seeded", len(strategies))
    except Exception as exc:
        logger.warning("  ⚠ Strategy seed failed: %s", exc)


# ════════════════════════════════════════════════════════════════════════════
# STEP 14 — Legal consents
# ════════════════════════════════════════════════════════════════════════════

async def step_seed_legal(db, users: dict) -> None:
    logger.info("▶ Step 14: Seeding legal consents...")
    from sqlalchemy import select
    from app.models.legal import LegalConsent

    for email, user in users.items():
        exists = await db.execute(
            select(LegalConsent).where(LegalConsent.user_id == user.id)
        )
        if not exists.scalar_one_or_none():
            db.add(LegalConsent(
                user_id=user.id,
                accepted_at=datetime.now(timezone.utc),
            ))
    await db.commit()
    logger.info("  ✓ Legal consents seeded")


# ════════════════════════════════════════════════════════════════════════════
# STEP 15 — Warm Redis cache
# ════════════════════════════════════════════════════════════════════════════

async def step_warm_cache() -> None:
    logger.info("▶ Step 15: Warming Redis cache...")
    try:
        from app.db.redis_client import init_redis
        await init_redis()
        logger.info("  ✓ Redis connected")
    except Exception as exc:
        logger.warning("  ⚠ Redis warm failed: %s", exc)


# ════════════════════════════════════════════════════════════════════════════
# STEP 16 — Print summary
# ════════════════════════════════════════════════════════════════════════════

def print_summary(symbols: list[str]) -> None:
    print("\n" + "═" * 65)
    print("  FIN-EYE SEED COMPLETE")
    print("═" * 65)
    print(f"  Symbols seeded : {', '.join(symbols[:8])}{'...' if len(symbols) > 8 else ''}")
    print(f"  Admin login    : {ADMIN_EMAIL}  /  {ADMIN_PASSWORD}")
    print(f"  Demo login     : {DEMO_EMAIL}  /  {DEMO_PASSWORD}")
    print(f"  Pro login      : {PRO_EMAIL}  /  {PRO_PASSWORD}")
    print()
    print("  App URLs:")
    print("    Frontend   → http://localhost:3000")
    print("    API docs   → http://localhost:8000/docs")
    print("    Admin ops  → http://localhost:3000/admin")
    print("═" * 65 + "\n")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

async def main(args: argparse.Namespace) -> None:
    symbols = (
        [s.strip().upper() for s in args.symbols.split(",")]
        if args.symbols
        else DEFAULT_SYMBOLS
    )

    logger.info("═" * 60)
    logger.info("  FIN-EYE SEEDER  |  symbols=%d  skip_ml=%s  fast=%s",
                len(symbols), args.skip_ml, args.fast)
    logger.info("═" * 60)

    # Step 1 — DB
    step_init_db()

    async with AsyncSessionLocal() as db:
        # Step 2 — Users
        users = await step_seed_users(db)

        if not args.demo_only:
            # Step 3 — OHLCV
            await step_seed_ohlcv(db, symbols, fast=args.fast)

            # Step 4 — News
            if not args.fast:
                await step_seed_news(db, symbols)

            # Step 5 — Macro
            await step_seed_macro(db)

            # Step 6 — GAS
            if not args.skip_ml:
                await step_seed_gas(db, symbols, skip_ml=args.skip_ml)
            else:
                logger.info("▶ Step 6: Skipping GAS/ML (--skip-ml flag)")

        # Step 7 — Watchlist
        await step_seed_watchlist(db, users)

        # Step 8 — Portfolio
        await step_seed_portfolio(db, users)

        # Step 9 — Custom Indicators
        await step_seed_indicators(db, users)

        # Step 10 — Blog
        await step_seed_blog(db)

        # Step 11 — Showcase
        await step_seed_showcase(db)

        # Step 12 — Alerts
        await step_seed_alerts(db, users)

        # Step 13 — Strategies
        await step_seed_strategies(db, users)

        # Step 14 — Legal
        await step_seed_legal(db, users)

    # Step 15 — Cache
    await step_warm_cache()

    # Step 16 — Summary
    print_summary(symbols)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fin-Eye full data seeder")
    parser.add_argument("--symbols",    default="",    help="Comma-separated ticker list (default: all)")
    parser.add_argument("--skip-ml",    action="store_true", help="Skip ML training + GAS compute")
    parser.add_argument("--fast",       action="store_true", help="Only seed critical path data")
    parser.add_argument("--demo-only",  action="store_true", help="Only seed users/watchlists")
    parser.add_argument("--reset",      action="store_true", help="Drop + recreate all tables (DESTRUCTIVE)")
    args = parser.parse_args()

    if args.reset:
        confirm = input("⚠  --reset will DROP all tables. Type 'yes' to confirm: ").strip()
        if confirm != "yes":
            print("Aborted.")
            sys.exit(0)
        logger.warning("Dropping all tables...")
        from app.db.database import Base, engine
        import sqlalchemy as sa
        with engine.begin() as conn:
            Base.metadata.drop_all(conn)
        logger.info("All tables dropped. Proceeding with seed...")

    asyncio.run(main(args))
