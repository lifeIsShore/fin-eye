"""
Seed script: populate the Showcase / Pro Tools catalogue.

Usage (from backend/ directory):
    python scripts/seed_showcase.py

Idempotent — skips products whose title already exists.
Edit PRODUCTS below to add/change the catalogue without touching the DB manually.
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal
from app.models.showcase import ShowcaseProduct

# ─── Product catalogue ────────────────────────────────────────────────────────

PRODUCTS = [
    {
        "title": "Portfolio Risk Dashboard Template",
        "tagline": "A ready-made Excel/Google Sheets template for tracking portfolio risk metrics.",
        "description": (
            "Stop building spreadsheets from scratch. This template includes pre-wired "
            "calculations for beta-adjusted exposure, sector concentration, max drawdown "
            "tracking, and a simple correlation heatmap. Works with manual data entry or "
            "a data feed. Includes a 10-page setup guide."
        ),
        "features": [
            "Beta-adjusted exposure tracker",
            "Sector concentration pie chart",
            "Rolling max drawdown calculator",
            "Correlation heatmap (up to 20 assets)",
            "One-click PDF export of summary page",
            "Compatible with Excel 2016+ and Google Sheets",
        ],
        "category": "Portfolio Tools",
        "price_label": "$29 one-time",
        "external_url": "https://example.com/products/portfolio-risk-template?source=terminal",
        "sort_order": 10,
    },
    {
        "title": "Macro Regime Cheat Sheet",
        "tagline": "A concise reference card mapping macro regimes to historical asset class performance.",
        "description": (
            "A beautifully formatted 2-page PDF reference covering the four core macro "
            "regimes (Risk-On / Risk-Off / Inflationary / Deflationary) and how equities, "
            "bonds, commodities, and cash have historically performed in each. Includes a "
            "quick-reference decision matrix for portfolio tilt."
        ),
        "features": [
            "Four-regime framework with historical returns",
            "Asset class performance by regime (equities, bonds, gold, cash)",
            "Quick-reference decision matrix",
            "Compatible with Fin-Eye's GAS and regime output",
            "Printable A4/Letter PDF format",
        ],
        "category": "Planning Tools",
        "price_label": "$9 one-time",
        "external_url": "https://example.com/products/macro-regime-cheatsheet?source=terminal",
        "sort_order": 20,
    },
    {
        "title": "Backtesting Journal Template",
        "tagline": "Track, compare and improve your backtests with a structured journal.",
        "description": (
            "A Google Sheets template designed to help you maintain a rigorous backtest "
            "journal: record strategy parameters, capture key metrics (Sharpe, max DD, "
            "win rate), note live vs. backtest degradation, and track strategy evolution "
            "over time. Includes a comparison dashboard across all logged strategies."
        ),
        "features": [
            "Strategy parameter log (SMA, RSI, thresholds etc.)",
            "Automated metrics comparison chart",
            "Live vs. backtest degradation tracker",
            "Walk-forward result tracking",
            "Pre-filled with 5 example strategy entries",
            "Compatible with Google Sheets and Excel",
        ],
        "category": "Planning Tools",
        "price_label": "$19 one-time",
        "external_url": "https://example.com/products/backtest-journal?source=terminal",
        "sort_order": 30,
    },
    {
        "title": "Options Hedge Calculator",
        "tagline": "A spreadsheet tool for sizing protective puts and collars on individual positions.",
        "description": (
            "Enter your position size, stock price, and target protection level. The tool "
            "calculates the number of contracts needed, estimated annualised premium cost, "
            "and shows you a payoff diagram for protective put and collar strategies. Uses "
            "Black-Scholes approximation for cost estimation (no live feed required)."
        ),
        "features": [
            "Protective put sizing calculator",
            "Collar strategy analyser (put + short call)",
            "Black-Scholes premium approximation",
            "Interactive payoff diagram",
            "Annualised cost vs. protection level trade-off chart",
            "Works offline — no API keys required",
        ],
        "category": "Portfolio Tools",
        "price_label": "$39 one-time",
        "external_url": "https://example.com/products/options-hedge-calculator?source=terminal",
        "sort_order": 40,
    },
    {
        "title": "Financial Ratios Quick Reference",
        "tagline": "Every ratio you need for equity analysis — definitions, formulas, benchmarks.",
        "description": (
            "A comprehensive but concise PDF reference covering 60+ financial ratios "
            "across valuation (P/E, EV/EBITDA, P/B), profitability (ROE, ROIC, margins), "
            "liquidity, leverage, and growth. Each ratio includes the formula, what it "
            "measures, and rule-of-thumb benchmarks by sector. Perfect as a desk reference "
            "or revision tool."
        ),
        "features": [
            "60+ ratios across 5 categories",
            "Formula + interpretation for each ratio",
            "Sector benchmark ranges",
            "Valuation multiples comparison table",
            "Printable A4/Letter PDF — 12 pages",
        ],
        "category": "Educational",
        "price_label": "$7 one-time",
        "external_url": "https://example.com/products/financial-ratios-reference?source=terminal",
        "sort_order": 50,
    },
    {
        "title": "Sector Rotation Playbook",
        "tagline": "When to rotate into and out of each sector across the economic cycle.",
        "description": (
            "A practical guide to sector rotation strategy mapped against the economic "
            "cycle (early expansion → late expansion → slowdown → recession → recovery). "
            "Covers 11 GICS sectors with historical performance data, typical timing signals, "
            "and integration notes for using Fin-Eye's macro score to guide rotation decisions."
        ),
        "features": [
            "11 GICS sectors mapped to economic cycle phases",
            "Historical performance by cycle phase",
            "Macro score trigger levels for each rotation",
            "Top ETF examples per sector",
            "Educational framework — not trade recommendations",
            "15-page PDF guide",
        ],
        "category": "Educational",
        "price_label": "$24 one-time",
        "external_url": "https://example.com/products/sector-rotation-playbook?source=terminal",
        "sort_order": 60,
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
    print("Seeding Showcase products…")
    seed()
