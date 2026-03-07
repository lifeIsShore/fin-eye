"""
Seed script: foundational educational blog posts for the Learn section.

Posts inserted:
  1. What Is the Global Alignment Score (GAS)?
  2. How to Read the Yield Curve — and Why It Matters
  3. Understanding Market Regimes: Risk-On vs Risk-Off
  4. How to Use the Fin-Eye Stress Index

Usage (from backend/ directory):
    python scripts/seed_learn_articles.py

Idempotent: skips any slug that already exists in the database.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal
from app.models.blog import BlogPost

# ─── Article content ─────────────────────────────────────────────────────────

POSTS = [
    # ── 1. GAS Explainer ─────────────────────────────────────────────────────
    {
        "title":       "What Is the Global Alignment Score (GAS)?",
        "slug":        "what-is-the-global-alignment-score",
        "summary":     (
            "The GAS is Fin-Eye's headline number — a single 0–100 score that combines "
            "macro conditions, news sentiment, and technical signals to describe the "
            "current market environment for any asset."
        ),
        "category":    "How It Works",
        "read_time":   "7 min read",
        "author":      "Fin-Eye Research",
        "published_at": datetime(2026, 1, 10),
        "content_md":  """\
# What Is the Global Alignment Score (GAS)?

The **Global Alignment Score** is the headline number you see at the top of every asset
page in Fin-Eye. It's a single integer from **0 to 100** that answers one question:

> *"How aligned are current macro conditions, market sentiment, and technical signals
> for this asset — and in which direction?"*

A high score (70–100) means the three layers are broadly pointing in the same supportive
direction. A low score (0–30) means conditions are stressed, bearish, or contradictory.
A mid-range score (30–70) reflects mixed or transitional conditions.

---

## The Three Layers

GAS is built from three independent signal layers, each scored 0–100:

### 1. Macro Layer (30% weight)
This layer reflects the macroeconomic backdrop:
- **Yield curve shape** — slope of the 2–10 year Treasury spread
- **Fed Funds Rate** relative to neutral
- **Unemployment trend**
- **CPI inflation** trajectory
- **Financial Stress Index** from the St. Louis Fed

Each indicator is scored on a 0–100 sub-scale. The macro score changes slowly — it
captures the tide, not the waves.

### 2. News Sentiment Layer (30% weight)
Uses a FinBERT-based natural language model trained on financial text to score the
tone of recent news coverage for each asset.

- 30-day rolling window of news headlines and articles
- Each article scored on a -1 to +1 scale (bearish → bullish)
- Aggregated into a 0–100 sub-score

Sentiment captures market mood and can move quickly around earnings, policy decisions,
or macro events.

### 3. Technical Layer (40% weight)
Multi-timeframe technical signal analysis across five timeframes:
**1-hour, 4-hour, daily, weekly, monthly**

Each timeframe generates a Bullish / Neutral / Bearish classification based on:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence/Divergence)
- Bollinger Bands
- Moving average alignment

The timeframe scores are weighted (longer timeframes carry more weight) and combined
into a 0–100 Technical Confidence Score.

---

## How GAS Is Calculated

```
GAS = (Technical Score × 0.40) + (Sentiment Score × 0.30) + (Macro Score × 0.30)
```

Each layer contributes independently. A macro shock doesn't automatically affect
technical signals — and that's intentional. When the layers **disagree**, the
Conflict Detector fires and you'll see an explanation of the divergence.

---

## Weather Metaphor

Rather than showing raw numbers everywhere, Fin-Eye translates GAS into a
**weather state** — a more intuitive way to think about market conditions:

| GAS Range | Weather State | Meaning |
|-----------|--------------|---------|
| 75–100 | ☀️ Mild Support | All layers broadly bullish |
| 55–74 | 🌤 Mixed Signals | No clear consensus |
| 35–54 | 🌧 Headwind | Bearish pressure building |
| 0–34 | ⛈ High Instability | Significant stress across layers |

These are descriptions of the *environment*, not buy or sell signals.

---

## What GAS Is NOT

GAS is an **educational context tool**, not a trading signal generator.

- A GAS of 80 does not mean "buy this asset"
- A GAS of 10 does not mean "sell everything"
- GAS does not incorporate position sizing, risk tolerance, or time horizon

Use GAS to understand the broader environment an asset is operating in.
For a deeper view, click into any of the three layers to see the underlying data.

---

## Example: Reading a GAS of 42

Suppose you're looking at an asset with GAS = 42 ("Headwind"):

- Technical Score: 55 (mildly bearish trend signals on shorter timeframes)
- Sentiment Score: 38 (negative news coverage in past 30 days)
- Macro Score: 28 (inverted yield curve, rising unemployment trend)

The conflict detector might flag: *"Technical signals are relatively neutral while
macro is stressed — consider whether short-term price action is reflecting underlying
deterioration."*

This doesn't tell you to sell. It tells you the macro backdrop is hostile while
price hasn't fully reflected that yet — a situation worth being aware of.

---

## Summary

GAS brings together three different analytical lenses — macro, sentiment, and technical —
into a single, unified view of market conditions. It's designed to help you ask better
questions, not to answer them for you. Explore each layer to understand *why* the score
is what it is.
""",
    },

    # ── 2. Yield Curve Explainer ──────────────────────────────────────────────
    {
        "title":       "How to Read the Yield Curve — and Why It Matters",
        "slug":        "how-to-read-the-yield-curve",
        "summary":     (
            "The yield curve is one of the most reliable leading indicators in economics. "
            "Here's what inversion means, why it matters for equity markets, and how "
            "Fin-Eye incorporates it into the macro layer."
        ),
        "category":    "Macro Fundamentals",
        "read_time":   "8 min read",
        "author":      "Fin-Eye Research",
        "published_at": datetime(2026, 1, 20),
        "content_md":  """\
# How to Read the Yield Curve — and Why It Matters

The yield curve is a simple chart, but it encodes an enormous amount of information
about where the economy is headed. It's one of the few indicators with a genuine
track record of predicting recessions — which is why Fin-Eye uses it as a core
input to the macro layer.

---

## What Is the Yield Curve?

Bonds come with different **maturity dates** — 3 months, 2 years, 10 years, 30 years.
The **yield** on each bond is the annual return an investor receives for holding it
to maturity.

In normal conditions, longer-maturity bonds yield more than shorter ones — investors
demand a premium for locking up money for longer. This produces an **upward-sloping**
(normal) yield curve.

The yield curve Fin-Eye monitors most closely is the **2-year vs. 10-year US Treasury spread**
(written as 10Y–2Y). When this spread is:

- **Positive** → 10Y yield > 2Y yield → normal, upward-sloping curve
- **Near zero** → flattening curve → uncertainty about growth
- **Negative** → 10Y yield < 2Y yield → **inverted** curve

---

## What Does Inversion Mean?

When short-term rates (2-year) exceed long-term rates (10-year), the market is signalling:

1. **Tight monetary policy**: The Fed has raised short-term rates, making short bonds
   yield more than long ones
2. **Pessimistic long-run growth expectations**: Investors don't expect the economy to
   grow strongly, so they're willing to accept lower yields on long bonds in exchange
   for safety

In other words: the bond market is collectively betting that growth will slow —
often dramatically.

---

## The Recession Track Record

The 10Y–2Y inversion has preceded every US recession since 1955, with only one
false signal in that entire period. The lead time is typically **6–18 months** after
inversion begins.

| Inversion Date | Recession Start | Lead Time |
|----------------|-----------------|-----------|
| Dec 1988 | Jul 1990 | ~19 months |
| Feb 2000 | Mar 2001 | ~13 months |
| Jan 2006 | Dec 2007 | ~23 months |
| Mar 2019 | Feb 2020 | ~11 months |
| Jul 2022 | ? (as of 2026) | TBD |

**Important caveat:** "Preceded every recession" is not the same as "predicts the
exact timing or severity." The 2019 inversion was followed by a COVID-induced recession —
not a credit crisis. Lead times vary widely.

---

## How Fin-Eye Uses the Yield Curve

The 10Y–2Y spread (sourced daily from FRED) feeds directly into the **macro layer**
of the GAS score. The contribution is non-linear:

| Spread | Macro Contribution | Label |
|--------|-------------------|-------|
| > +1.5% | Strongly positive | Steep / accommodative |
| +0.5% to +1.5% | Positive | Normal |
| 0% to +0.5% | Slightly positive | Flattening |
| -0.5% to 0% | Negative | Mildly inverted |
| < -0.5% | Strongly negative | Inverted / stressed |

A deeply inverted yield curve can alone drag the macro score to "Stressed" territory
even if other macro indicators remain healthy.

---

## The Yield Curve Page in Fin-Eye

On the **Macro** page, you'll find the full yield curve visualisation showing all
major Treasury maturities from 3-month to 30-year. Key things to look at:

- **Shape**: Is it upward sloping (normal) or inverted anywhere?
- **Trend**: Is the curve steepening or flattening compared to 30/90 days ago?
- **Historical context**: The sparkline overlay shows where each maturity stood
  a month ago so you can see direction at a glance

The **Recession Gauge** next to the yield curve translates the 10Y–2Y spread into
a probability estimate using a logistic regression model fitted on post-1955 data.
A gauge above 40% has historically been associated with elevated recession risk over
the following 12 months.

---

## Common Misunderstandings

**"Inversion means the market will crash immediately."**
No — inversion is a *leading* indicator, typically 6–18 months ahead. Markets often
continue to make new highs for months after the curve first inverts.

**"The yield curve always predicts recessions."**
It has a strong track record but is not infallible. No single indicator is. The 1998
inversion was followed by a slowdown, not a full recession. Always look at the full
GAS picture.

**"Now that the curve is uninverting, the danger is over."**
Historically, the most dangerous period for equities is often the **re-steepening**
that follows inversion — because it typically reflects an abrupt Fed pivot (rate cuts)
in response to economic deterioration, not healing.

---

## Takeaway

The yield curve is a slow-moving signal — but a powerful one. When it inverts, it
doesn't tell you *when* trouble will arrive, but it substantially raises the probability
that macro conditions will deteriorate over the following 12–24 months. Combined with
sentiment and technical data in the GAS framework, it helps build a fuller picture
of the environment you're operating in.
""",
    },

    # ── 3. Market Regimes ─────────────────────────────────────────────────────
    {
        "title":       "Understanding Market Regimes: Risk-On vs Risk-Off",
        "slug":        "understanding-market-regimes-risk-on-risk-off",
        "summary":     (
            "Markets don't behave the same way all the time. Understanding the difference "
            "between risk-on and risk-off regimes — and how to spot transitions between "
            "them — is one of the most practical skills in macro investing."
        ),
        "category":    "Macro Fundamentals",
        "read_time":   "6 min read",
        "author":      "Fin-Eye Research",
        "published_at": datetime(2026, 2, 5),
        "content_md":  """\
# Understanding Market Regimes: Risk-On vs Risk-Off

Markets don't move in a straight line — they cycle through distinct **regimes** where
investor behaviour, asset correlations, and volatility patterns change dramatically.
Understanding which regime you're in is arguably more important than picking individual
stocks.

---

## What Is a Market Regime?

A regime is a persistent state of the market characterised by consistent patterns
of asset pricing, volatility, and correlations. The simplest and most useful
distinction is between:

- **Risk-On**: Investors are comfortable taking risk. Equities rise, spreads compress,
  safe-haven assets (gold, USD, Treasuries) underperform. Volatility is low.

- **Risk-Off**: Investors flee risk. Equities fall, bonds and gold rally, high-yield
  spreads widen. Volatility spikes. Defensive sectors outperform cyclicals.

Most market participants intuitively understand this framework, but few have a
systematic way to measure which regime they're in.

---

## How Fin-Eye Classifies Regimes

The Technical Layer in Fin-Eye uses a VIX-based volatility regime to contextualise
technical signals:

| VIX Level | Volatility Regime | Typical Behaviour |
|-----------|------------------|------------------|
| < 15 | Low | Trending, mean-reversion works well |
| 15–25 | Normal | Standard technical signals apply |
| 25–35 | Elevated | Breakouts often fail, increased gap risk |
| > 35 | High | Extreme moves, technical signals less reliable |

Within each volatility regime, the multi-timeframe signals determine whether the
overall environment is Risk-On, Risk-Off, or transitional.

A **Risk-On** classification requires at least 3 of 5 timeframes to be Bullish
with VIX below 20. A **Risk-Off** classification requires at least 3 of 5 timeframes
to be Bearish, and/or VIX above 25.

---

## Regime Transitions: The Most Dangerous Moments

The most costly mistakes in investing often happen **at regime transitions** — when
a bull market tips into a bear market (or vice versa) and participants are slow to
recognise the shift.

### Signs of a Risk-On → Risk-Off transition:
- Higher-timeframe technical signals (weekly, monthly) start flipping Bearish
- VIX begins a sustained move above 20
- Macro data deteriorates (yield curve flattening/inverting, unemployment rising)
- News sentiment turns negative for broad market
- Defensive sectors (utilities, consumer staples) outperform

### Signs of a Risk-Off → Risk-On transition:
- Central bank policy pivot (rate cuts, QE announcement)
- VIX collapses below 20
- Monthly and weekly technical signals rebuild to Bullish
- Credit spreads tighten
- Cyclical sectors start leading

The GAS score doesn't tell you "now is the transition" — but the Conflict Detector
often fires at these moments, flagging that technical and macro layers are pointing
in opposite directions.

---

## The Multi-Timeframe Cascade

One of the most reliable patterns in regime analysis is the **cascade** — how
changes in regime propagate from shorter to longer timeframes (in rapid selloffs)
or from longer to shorter timeframes (in slower deteriorations).

**Rapid shock (e.g. COVID-19 2020):**
```
1h → 4h → 1d → 1w → 1m
Risk-Off signal spreads in days
```

**Slow deterioration (e.g. 2007–2008):**
```
1m → 1w → 1d → 4h → 1h
Monthly signals turn first, hours later confirm
```

In Fin-Eye's Technical page, you can see all five timeframes simultaneously. A 
cascade in progress — where some timeframes have flipped while others haven't —
is often a sign that a regime transition is underway.

---

## Practical Implications

Understanding regime isn't just an academic exercise. Different strategies work
better in different regimes:

**In Risk-On / Low Volatility:**
- Trend-following strategies tend to work well
- Growth and cyclical sectors outperform
- Technical signals are more reliable (cleaner trends)

**In Risk-Off / High Volatility:**
- Mean-reversion signals are less reliable (gaps, extreme moves)
- Technical levels can be violated without consequence
- Macro and sentiment data become more important than price action

**At Transitions:**
- The conflict detector in Fin-Eye is specifically designed to identify when
  technical signals are diverging from macro conditions
- These are the moments to be most cautious about over-relying on any single signal

---

## The Regime Widget

On the Fin-Eye dashboard, the **Regime Widget** shows the current classification
(Risk-On, Transitional, or Risk-Off) alongside the VIX level and a 5-dot display
showing the current status of each timeframe. This gives you an immediate visual
sense of how many timeframes are aligned and in which direction.

A single glance tells you: are we in a clear environment, or are we at a transition
point where different timeframes disagree?

---

## Summary

Market regimes are real, persistent, and consequential. The Risk-On / Risk-Off
framework is one of the most useful mental models for understanding the broad
investment environment. Fin-Eye operationalises this through multi-timeframe
technical classification, VIX regime tracking, and the Conflict Detector —
giving you a systematic way to identify where you are in the cycle.
""",
    },

    # ── 4. Stress Index ───────────────────────────────────────────────────────
    {
        "title":       "How to Use the Fin-Eye Stress Index",
        "slug":        "how-to-use-the-stress-index",
        "summary":     (
            "The Stress Index combines five macro indicators into a single measure of "
            "financial system health. Here's what goes into it, how to interpret it, "
            "and what its historical readings have meant for markets."
        ),
        "category":    "How It Works",
        "read_time":   "5 min read",
        "author":      "Fin-Eye Research",
        "published_at": datetime(2026, 2, 20),
        "content_md":  """\
# How to Use the Fin-Eye Stress Index

The **Stress Index** is a single composite number that summarises the overall health
of the macroeconomic and financial environment. It draws on the same data that feeds
the macro layer of GAS, but presents it as a standalone gauge — useful for quickly
assessing whether the financial system is calm, under pressure, or in crisis.

---

## What Goes Into the Stress Index?

The Stress Index is calculated from five components:

| Component | Source | What It Measures |
|-----------|--------|-----------------|
| Yield Curve (10Y–2Y spread) | FRED: T10Y2Y | Recession risk signal |
| St. Louis Financial Stress Index | FRED: STLFSI4 | Broad financial conditions |
| Fed Funds Rate vs. Neutral | FRED: FEDFUNDS | Monetary policy tightness |
| Unemployment Trend (MoM change) | FRED: UNRATE | Labour market health |
| CPI Inflation (YoY trend) | FRED: CPIAUCSL | Inflationary pressure |

Each component is normalised to a 0–100 scale where **100 = maximum stress** and
**0 = minimal stress**. The components are then averaged with equal weighting.

---

## Reading the Gauge

The Stress Index gauge on the Macro page uses a traffic-light colour scheme:

| Range | Label | What It Means |
|-------|-------|---------------|
| 0–20 | 🟢 Low Stress | Financial conditions are supportive. Monetary policy accommodative or neutral. Unemployment stable. |
| 20–40 | 🟡 Moderate | Some headwinds present. Monitor for deterioration. |
| 40–65 | 🟠 Elevated | Multiple stress indicators are flashing. Increased caution warranted. |
| 65–100 | 🔴 High Stress | Crisis-level conditions across multiple indicators. |

In most non-crisis years, the index ranges between 15–35. Readings above 50 have
historically coincided with recessions or major market dislocations.

---

## Historical Reference Points

To calibrate your interpretation, here are approximate Stress Index readings at
key historical moments (reconstructed):

| Period | Approximate Reading | Context |
|--------|--------------------|---------| 
| 2005–2006 | 18–25 | Pre-GFC calm, mild yield curve flattening |
| Q4 2008 | 88–95 | Peak GFC — Lehman, bank runs, Fed emergency actions |
| Mid-2009 | 65–75 | Still elevated but recovering post-QE1 |
| 2017–2019 | 15–30 | Low volatility era |
| Q1 2020 (COVID) | 72–85 | Rapid shock — spike and fast recovery |
| 2022–2023 | 45–60 | Fed tightening cycle, yield curve inversion |

---

## How to Use It in Practice

**As a regime filter:**
When the Stress Index is below 25, technical signals tend to be more reliable —
markets are trending cleanly and macro noise is low. When it's above 50, be more
skeptical of technical breakouts and bullish signals.

**As a context layer:**
A GAS score of 70 in a Stress Index = 18 environment is very different from a
GAS of 70 in a Stress Index = 55 environment. The latter might reflect a temporary
technical rally against a deteriorating macro backdrop — exactly the kind of conflict
the Conflict Detector is designed to flag.

**As a historical anchor:**
The 30-day sparkline on the Stress Index gauge shows whether conditions are improving
or deteriorating. A rising index over 30 days is a warning sign even if the absolute
level is not yet alarming.

---

## Limitations

- The Stress Index uses **monthly-frequency FRED data** for most components.
  This means it lags fast-moving market events by days to weeks.
- It measures *macro and financial* stress, not market *price* stress. The 2022
  equity bear market saw a moderately elevated stress index — but prices still fell
  significantly.
- It is best used as **one input among many**, not as a standalone signal.

---

## Summary

The Stress Index condenses five macro and financial health indicators into a single
intuitive gauge. Use it as a quick check on the macro environment before diving
into individual assets — it tells you whether you're fishing in calm waters or
in the middle of a storm.
""",
    },
]


# ─── Seed function ────────────────────────────────────────────────────────────

def seed() -> None:
    db = SessionLocal()
    inserted = 0
    skipped  = 0
    try:
        for p in POSTS:
            existing = db.query(BlogPost).filter(BlogPost.slug == p["slug"]).first()
            if existing:
                print(f"  SKIP  '{p['slug']}' already exists.")
                skipped += 1
                continue

            post = BlogPost(
                title       = p["title"],
                slug        = p["slug"],
                summary     = p["summary"],
                category    = p["category"],
                read_time   = p["read_time"],
                author      = p["author"],
                content_md  = p["content_md"],
                status      = "published",
                published_at = p["published_at"],
                created_at  = p["published_at"],
                updated_at  = p["published_at"],
            )
            db.add(post)
            print(f"  ADD   '{p['slug']}'")
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
    print("Seeding foundational Learn articles…\n")
    seed()
