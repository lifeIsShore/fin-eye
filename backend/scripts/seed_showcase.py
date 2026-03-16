"""
Seed script: populate the Showcase / Pro Tools catalogue.

Usage (from backend/ directory):
    python scripts/seed_showcase.py

Idempotent — skips products whose title already exists.
Run again after adding new products to insert only the new ones.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal
from app.models.showcase import ShowcaseProduct

# ─── Product catalogue ────────────────────────────────────────────────────────
# Categories: "Templates" | "Portfolio Tools" | "Education" | "Workflow" | "Integrations"

PRODUCTS = [

    # ── Templates ──────────────────────────────────────────────────────────────
    {
        "title": "GAS Score Interpretation Cheat Sheet",
        "tagline": "Understand every Fin-Eye score at a glance — a must-have desk reference.",
        "description": (
            "A beautifully formatted 2-page PDF that explains every score and label Fin-Eye "
            "produces: GAS ranges (Strong Tailwind → High Instability), signal grades (A+ → F), "
            "regime labels (Risk-On / Transitional / Risk-Off), and how the three components "
            "combine. Includes a decision matrix for common signal combinations. "
            "Perfect to print and keep at your desk."
        ),
        "features": [
            "GAS score ranges with plain-English interpretation",
            "Signal grade breakdown (A+ → F) with tradeable thresholds",
            "Component score reading guide (Technical / Sentiment / Macro)",
            "Conflict detector interpretation notes",
            "Regime labels and what they mean for positioning",
            "Printable A4/Letter PDF — 2 pages",
        ],
        "category": "Templates",
        "price_label": "Free",
        "external_url": "https://example.com/products/gas-cheat-sheet?source=terminal",
        "sort_order": 10,
    },
    {
        "title": "Multi-Timeframe Signal Checklist",
        "tagline": "A structured pre-trade checklist that maps 1h/4h/1d/1wk signals to entry criteria.",
        "description": (
            "Stop second-guessing entries. This Google Sheets + PDF template walks you through "
            "a 12-point pre-trade checklist: GAS score gate, timeframe agreement check, "
            "sentiment alignment, macro regime confirmation, and risk/reward validation. "
            "Includes a traffic-light scoring system so you can see at a glance whether all "
            "layers are aligned before acting."
        ),
        "features": [
            "12-point pre-trade checklist",
            "Traffic-light scoring: Green / Amber / Red per layer",
            "Timeframe agreement calculator (1h/4h/1d/1wk)",
            "Macro regime gate with GAS score threshold",
            "Editable Google Sheets + printable PDF",
            "Includes 3 worked example trades",
        ],
        "category": "Templates",
        "price_label": "$12 one-time",
        "external_url": "https://example.com/products/signal-checklist?source=terminal",
        "sort_order": 20,
    },
    {
        "title": "Macro Regime Cheat Sheet",
        "tagline": "Four macro regimes mapped to historical asset class performance.",
        "description": (
            "A concise 2-page PDF reference covering the four core macro regimes "
            "(Risk-On / Risk-Off / Inflationary / Deflationary) and how equities, bonds, "
            "commodities, and cash have historically performed in each. Includes a "
            "quick-reference decision matrix for portfolio tilt and integration notes "
            "for using Fin-Eye's macro score."
        ),
        "features": [
            "Four-regime framework with historical return data",
            "Asset class performance by regime (equities, bonds, gold, cash)",
            "Quick-reference tilt decision matrix",
            "Macro score thresholds for each regime",
            "Printable A4/Letter PDF — 2 pages",
        ],
        "category": "Templates",
        "price_label": "$9 one-time",
        "external_url": "https://example.com/products/macro-regime-cheatsheet?source=terminal",
        "sort_order": 30,
    },

    # ── Portfolio Tools ────────────────────────────────────────────────────────
    {
        "title": "Position Sizing Calculator",
        "tagline": "Input your GAS grade and account size — get exact position sizes instantly.",
        "description": (
            "A Google Sheets tool that automates grade-based position sizing. Enter your "
            "account size, risk tolerance (%), and the signal grade for each position. "
            "The tool calculates maximum position size per the grade rules: A+ → up to 20%, "
            "A → 15%, B → 10%, C → 5% (monitor only), D/F → 0%. Includes a portfolio "
            "summary view showing total deployed capital and sector concentration."
        ),
        "features": [
            "Grade-based position sizing (A+ through F)",
            "Account size and risk % inputs",
            "Auto-calculated max position per grade rule",
            "Portfolio summary: total deployed, cash reserve",
            "Sector concentration breakdown",
            "Compatible with Google Sheets and Excel",
        ],
        "category": "Portfolio Tools",
        "price_label": "$19 one-time",
        "external_url": "https://example.com/products/position-sizer?source=terminal",
        "sort_order": 40,
    },
    {
        "title": "Portfolio Risk Dashboard Template",
        "tagline": "Beta exposure, drawdown tracking, and correlation heatmap — all pre-built.",
        "description": (
            "Stop building risk dashboards from scratch. This Google Sheets template includes "
            "pre-wired calculations for beta-adjusted exposure, sector concentration, max "
            "drawdown tracking per position and portfolio-level, and a correlation heatmap "
            "for up to 20 assets. Works with manual data entry. Includes a 10-page setup guide."
        ),
        "features": [
            "Beta-adjusted exposure tracker",
            "Sector concentration chart",
            "Rolling max drawdown calculator per position",
            "Correlation heatmap (up to 20 assets)",
            "Portfolio-level P&L dashboard",
            "One-click PDF export of summary page",
        ],
        "category": "Portfolio Tools",
        "price_label": "$29 one-time",
        "external_url": "https://example.com/products/portfolio-risk-template?source=terminal",
        "sort_order": 50,
    },
    {
        "title": "Kelly Criterion & Risk/Reward Calculator",
        "tagline": "Calculate optimal position fractions and validate R:R before every trade.",
        "description": (
            "A compact Excel/Sheets tool combining the Kelly Criterion (optimal position "
            "fraction based on win rate and avg win/loss ratio) with a risk/reward validator. "
            "Enter your historical win rate, average win, and average loss to get full Kelly, "
            "half Kelly (recommended), and quarter Kelly sizing. Includes a sensitivity table "
            "and a 2-scenario R:R checker."
        ),
        "features": [
            "Full Kelly, Half Kelly, Quarter Kelly calculation",
            "Win rate + avg win/loss inputs",
            "Sensitivity table across win rate ranges",
            "Risk/Reward ratio validator (min 1:2 gate)",
            "Position size as % of account and dollar amount",
            "Includes worked examples for 5 trade scenarios",
        ],
        "category": "Portfolio Tools",
        "price_label": "$15 one-time",
        "external_url": "https://example.com/products/kelly-calculator?source=terminal",
        "sort_order": 60,
    },
    {
        "title": "Options Hedge Calculator",
        "tagline": "Size protective puts and collars on individual positions — no live feed needed.",
        "description": (
            "Enter your position size, stock price, and target protection level. The tool "
            "calculates the number of contracts needed, estimated annualised premium cost, "
            "and shows a payoff diagram for protective put and collar strategies. Uses "
            "Black-Scholes approximation for cost estimation. Works fully offline."
        ),
        "features": [
            "Protective put sizing calculator",
            "Collar strategy analyser (put + short call)",
            "Black-Scholes premium approximation",
            "Interactive payoff diagram",
            "Annualised cost vs. protection level chart",
            "Works offline — no API keys required",
        ],
        "category": "Portfolio Tools",
        "price_label": "$39 one-time",
        "external_url": "https://example.com/products/options-hedge-calculator?source=terminal",
        "sort_order": 70,
    },

    # ── Education ─────────────────────────────────────────────────────────────
    {
        "title": "Sector Rotation Playbook",
        "tagline": "When to rotate into and out of each sector across the economic cycle.",
        "description": (
            "A practical 15-page PDF guide to sector rotation strategy mapped against "
            "the economic cycle (early expansion → late cycle → slowdown → recession → recovery). "
            "Covers all 11 GICS sectors with historical performance data, typical timing "
            "signals, and how to use Fin-Eye's macro score and sector page to identify "
            "rotation opportunities."
        ),
        "features": [
            "11 GICS sectors mapped to economic cycle phases",
            "Historical performance by cycle phase",
            "Macro score trigger levels for each rotation signal",
            "Top ETF examples per sector (XLK, XLF, XLV...)",
            "Fin-Eye integration notes for each sector",
            "15-page PDF — educational framework only",
        ],
        "category": "Education",
        "price_label": "$24 one-time",
        "external_url": "https://example.com/products/sector-rotation-playbook?source=terminal",
        "sort_order": 80,
    },
    {
        "title": "Backtesting Interpretation Guide",
        "tagline": "What Sharpe, Sortino, and max drawdown actually mean — and when to trust a backtest.",
        "description": (
            "Most traders misread backtest results. This 20-page PDF guide explains every "
            "metric Fin-Eye's backtester produces: Sharpe Ratio, Sortino Ratio, max drawdown, "
            "recovery factor, win rate, and profit factor. Includes a practical overfitting "
            "detection checklist, walk-forward validation explained simply, and rules of "
            "thumb for what constitutes a 'good' backtest result in different market regimes."
        ),
        "features": [
            "Full explanation of all 8 Fin-Eye backtest metrics",
            "Overfitting detection checklist (5 warning signs)",
            "Walk-forward validation explained simply",
            "Benchmark comparison methodology",
            "'Good' result thresholds by asset class and timeframe",
            "20-page PDF with worked examples",
        ],
        "category": "Education",
        "price_label": "$17 one-time",
        "external_url": "https://example.com/products/backtest-guide?source=terminal",
        "sort_order": 90,
    },
    {
        "title": "Macro Indicator Deep Dive",
        "tagline": "What each FRED indicator means, how it behaves, and how Fin-Eye weights it.",
        "description": (
            "A 25-page educational PDF covering every macro indicator Fin-Eye tracks: "
            "Yield Curve (2Y/10Y spread), VIX, CPI YoY, Unemployment Rate, Fed Funds Rate, "
            "NFP, and Industrial Production. Each chapter covers: what the indicator measures, "
            "historical behaviour, leading vs lagging nature, and how it contributes to "
            "Fin-Eye's macro score calculation."
        ),
        "features": [
            "7 FRED indicators covered in depth",
            "Historical behaviour and typical ranges",
            "Leading vs lagging classification",
            "How each feeds into the Fin-Eye macro score",
            "Recession signal combinations explained",
            "25-page PDF — suitable for all experience levels",
        ],
        "category": "Education",
        "price_label": "$22 one-time",
        "external_url": "https://example.com/products/macro-deep-dive?source=terminal",
        "sort_order": 100,
    },
    {
        "title": "Financial Ratios Quick Reference",
        "tagline": "60+ ratios with formulas, interpretation, and sector benchmarks.",
        "description": (
            "A comprehensive 12-page PDF covering 60+ financial ratios across valuation "
            "(P/E, EV/EBITDA, P/B), profitability (ROE, ROIC, margins), liquidity, leverage, "
            "and growth. Each ratio includes the formula, what it measures, and rule-of-thumb "
            "benchmarks by sector. Perfect as a desk reference or revision tool."
        ),
        "features": [
            "60+ ratios across 5 categories",
            "Formula + interpretation for each ratio",
            "Sector benchmark ranges (tech, financials, industrials...)",
            "Valuation multiples comparison table",
            "Printable A4/Letter PDF — 12 pages",
        ],
        "category": "Education",
        "price_label": "$7 one-time",
        "external_url": "https://example.com/products/financial-ratios-reference?source=terminal",
        "sort_order": 110,
    },

    # ── Workflow ───────────────────────────────────────────────────────────────
    {
        "title": "Weekly Market Review Template",
        "tagline": "A Sunday ritual template: macro check, regime status, top signals, weekly plan.",
        "description": (
            "Build a consistent weekly market review habit with this Notion + Google Docs "
            "template. Sections: Macro Score Review (paste from Fin-Eye), Regime Status, "
            "Watchlist GAS Summary, Earnings Calendar for the week, Trade Plan for new setups, "
            "and a Reflection section for previous week's trades. Includes a 12-week "
            "cumulative tracker sheet."
        ),
        "features": [
            "6-section weekly review structure",
            "Macro + regime check-in prompts",
            "Watchlist GAS summary table (copy-paste ready)",
            "Earnings calendar section",
            "Trade plan template per setup",
            "12-week cumulative tracker — Notion + Google Docs versions",
        ],
        "category": "Workflow",
        "price_label": "$14 one-time",
        "external_url": "https://example.com/products/weekly-review-template?source=terminal",
        "sort_order": 120,
    },
    {
        "title": "Trade Journal Template",
        "tagline": "Log every trade with GAS context, grade at entry, and outcome tracking.",
        "description": (
            "A Google Sheets trade journal designed specifically for Fin-Eye users. Each "
            "entry captures: symbol, entry/exit date and price, GAS score at entry, signal "
            "grade at entry, timeframe consensus, stop loss, target, actual outcome, and "
            "notes. Dashboard tab shows win rate by grade, average R:R by regime, and a "
            "cumulative P&L curve."
        ),
        "features": [
            "Trade entry form with GAS + grade fields",
            "Auto-calculated R:R and outcome tracking",
            "Win rate breakdown by signal grade (A+ → F)",
            "Average performance by macro regime",
            "Cumulative P&L curve chart",
            "Includes 20 pre-filled example trades",
        ],
        "category": "Workflow",
        "price_label": "$18 one-time",
        "external_url": "https://example.com/products/trade-journal?source=terminal",
        "sort_order": 130,
    },
    {
        "title": "Backtesting Journal Template",
        "tagline": "Track, compare and iterate your backtests with a structured log.",
        "description": (
            "A Google Sheets template for maintaining a rigorous backtest journal: record "
            "strategy parameters, capture key metrics (Sharpe, max DD, win rate), note "
            "live vs. backtest degradation, and track strategy evolution over time. "
            "Includes a comparison dashboard across all logged strategies and a "
            "walk-forward tracking tab."
        ),
        "features": [
            "Strategy parameter log (SMA, RSI, thresholds...)",
            "Automated metrics comparison chart",
            "Live vs. backtest degradation tracker",
            "Walk-forward result tracking tab",
            "Pre-filled with 5 example strategy entries",
            "Compatible with Google Sheets and Excel",
        ],
        "category": "Workflow",
        "price_label": "$19 one-time",
        "external_url": "https://example.com/products/backtest-journal?source=terminal",
        "sort_order": 140,
    },
    {
        "title": "Watchlist Builder Notion Template",
        "tagline": "A Notion workspace to manage your symbols with GAS history and notes.",
        "description": (
            "A pre-built Notion template for managing your trading watchlist alongside "
            "Fin-Eye. Each symbol entry has fields for: sector, current GAS score, "
            "signal grade, last checked date, thesis notes, and a status tag "
            "(Watching / Entered / Exited / Shelved). Includes a board view by grade, "
            "a table view sorted by GAS score, and a weekly review checklist."
        ),
        "features": [
            "Per-symbol GAS score and grade tracking",
            "Thesis notes and status tags",
            "Board view organised by signal grade",
            "Table view sortable by GAS score",
            "Weekly review checklist built-in",
            "Notion template — duplicate to your workspace instantly",
        ],
        "category": "Workflow",
        "price_label": "Free",
        "external_url": "https://example.com/products/watchlist-notion?source=terminal",
        "sort_order": 150,
    },
]

# ─── Seed ─────────────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    inserted = skipped = 0
    try:
        for p in PRODUCTS:
            exists = db.query(ShowcaseProduct).filter(
                ShowcaseProduct.title == p["title"]
            ).first()
            if exists:
                print(f"  SKIP  '{p['title']}'")
                skipped += 1
                continue
            product = ShowcaseProduct(**p)
            db.add(product)
            print(f"  ADD   '{p['title']}'")
            inserted += 1
        db.commit()
        print(f"\nDone — {inserted} inserted, {skipped} skipped.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Seeding Showcase products…\n")
    seed()
