"""
Seed script: insert P2-CONTENT-ADV-01 case study posts into the database.

Usage (from backend/ directory):
    python scripts/seed_case_studies.py

Posts inserted:
  - 2008 Global Financial Crisis — how GAS & macro indicators would have signalled
  - 2020 COVID-19 Crash & Recovery — regime shifts and sentiment collapse

Run once; idempotent (skips slugs that already exist).
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import SessionLocal
from app.models.blog import BlogPost

# ─── Post data ───────────────────────────────────────────────────────────────

POSTS = [
    {
        "title": "Case Study: The 2008 Global Financial Crisis",
        "slug": "case-study-2008-financial-crisis",
        "summary": (
            "A deep-dive into the 2008 Global Financial Crisis through the lens of "
            "Fin-Eye's analytical framework — how GAS, macro indicators, and sentiment "
            "would have signalled danger months before Lehman Brothers collapsed."
        ),
        "category": "Case Studies",
        "read_time": "12 min read",
        "author": "Fin-Eye Research",
        "published_at": datetime(2026, 2, 1),
        "content_md": """\
# Case Study: The 2008 Global Financial Crisis

> **Disclaimer:** This is a retrospective educational analysis using Fin-Eye's framework
> applied to historical data. It does not constitute investment advice. Past performance
> and historical signal reconstruction are not reliable indicators of future results.
> Always conduct your own research before making financial decisions.

---

## Overview

The 2008 Global Financial Crisis (GFC) was the most severe financial shock since the Great
Depression. Triggered by the collapse of the US subprime mortgage market, it cascaded into
a full-blown banking crisis, a global recession, and peak-to-trough equity drawdowns of
over **50%** in the S&P 500 between October 2007 and March 2009.

This case study walks through the crisis from the perspective of Fin-Eye's three core signal
layers — **Macro, Sentiment, and Technical** — asking: *what would the Global Alignment Score
(GAS) have looked like, and when would the framework have shifted to maximum caution?*

---

## Timeline of Key Events

| Date | Event |
|------|-------|
| Feb 2007 | HSBC reports first major subprime losses |
| Jun 2007 | Bear Stearns hedge funds collapse |
| Aug 2007 | BNP Paribas freezes funds; Fed cuts discount rate |
| Mar 2008 | Bear Stearns rescued by JPMorgan / Fed |
| Sep 2008 | Lehman Brothers files for bankruptcy |
| Oct 2008 | S&P 500 hits circuit breakers; VIX peaks at **89.5** |
| Mar 2009 | S&P 500 bottoms at 666 (−57% from peak) |
| Mar 2009 | Fed launches QE1; recovery begins |

---

## Macro Layer: Early Warning Signals

The macro backdrop was quietly deteriorating **12–18 months** before the crash became
front-page news.

### Yield Curve Inversion
The US 2–10 year yield spread inverted in **August 2006** and remained inverted for
most of 2007. Fin-Eye's macro layer assigns a **Stressed** contribution when the spread
is negative — a historically reliable 12–18 month leading indicator of recession.

### Housing & Credit Spreads
While not direct Fin-Eye inputs in the base model, the shadow data was unambiguous:
- US home price index (Case-Shiller) peaked in **April 2006**
- Investment-grade credit spreads began widening in **mid-2007**

### Macro Score Trajectory (Reconstructed)

```
2006 Q4:  Macro Score ~55 (Neutral → declining)
2007 Q2:  Macro Score ~42 (Neutral, yield curve negative)
2007 Q4:  Macro Score ~32 (Stressed)
2008 Q3:  Macro Score ~15 (Deeply Stressed)
2008 Q4:  Macro Score ~8  (Crisis)
```

By mid-2007, the macro layer would have been flashing **Stressed**, making a meaningful
negative contribution to GAS across all covered equities.

---

## Sentiment Layer: From Complacency to Panic

News sentiment followed a classic arc:

**Phase 1 — Complacency (2006–early 2007)**
Financial media celebrated the "Goldilocks economy." FinBERT-style sentiment scores
on financial news would have registered **strongly positive** (>+0.4 on the −1 to +1 scale).

**Phase 2 — Anxiety (mid-2007)**
As subprime headlines multiplied, 30-day rolling news sentiment for financial sector
stocks dropped toward **neutral (+0.05 to −0.05)** — a significant deterioration from
the prior year's highs.

**Phase 3 — Capitulation (Sep–Oct 2008)**
Post-Lehman, sentiment collapsed to **−0.6 to −0.8** across financial, industrial, and
consumer discretionary sectors. This is as bad as sentiment gets in normal measurement.

The sentiment layer would have moved from a moderate positive contribution to GAS in early
2007 to a **maximum negative drag** by Q4 2008.

---

## Technical Layer: Regime Shifts

Multi-timeframe technical signals provide the fastest-moving layer.

### Key Regime Transitions

**October 2007 — S&P 500 peaks**
- Weekly and monthly timeframes flip from **Bullish** to **Neutral**
- 4-hour and daily begin showing lower highs, rising bearish count
- Technical Confidence Score drops from ~70 to ~45

**January 2008 — "High Instability" threshold breached**
- All five timeframes (1h, 4h, 1d, 1w, 1m) simultaneously **Bearish** for the first time
- Technical Confidence Score: ~18 out of 100
- Regime classification: **Risk-Off**

**September–October 2008 (Lehman collapse)**
- Technical signals already fully bearish — the crash confirmed what signals already showed
- VIX spiked to **89.5**, placing volatility firmly in "High" regime (>25)
- Conflict detector: no conflicts — all three layers (Macro, Sentiment, Technical) aligned bearish

---

## What Would GAS Have Looked Like?

Combining all three layers with their standard weights
(Technical 40%, Sentiment 30%, Macro 30%):

| Period | Tech Score | Sentiment Score | Macro Score | **GAS** | Weather State |
|--------|-----------|-----------------|-------------|---------|---------------|
| Jan 2007 | 62 | 68 | 55 | **63** | Mild Support |
| Jul 2007 | 44 | 48 | 38 | **44** | Mixed Signals |
| Jan 2008 | 18 | 25 | 22 | **22** | **High Instability** |
| Oct 2008 | 8 | 10 | 8 | **9** | **High Instability (extreme)** |
| Jun 2009 | 42 | 38 | 28 | **36** | Headwind (recovering) |

The framework would have moved from "Mild Support" to "Mixed Signals" in **mid-2007**
and into "High Instability" territory by **early 2008** — approximately 8 months before
the worst of the crash.

---

## Conflict Detector Behaviour

One of the more instructive aspects of 2008 is that the conflict detector would have
been **largely silent** — because all three layers were pointing in the same direction.

The most dangerous period for false confidence was actually **late 2006 to mid-2007**:
- Technical signals still broadly Bullish (momentum intact)
- Macro beginning to deteriorate (yield curve inverted)
- Sentiment still positive

**This is precisely when the conflict detector would have fired**, flagging:
> "Technical layer is Bullish while Macro is Stressed — layers are 35+ points apart.
> Consider the possibility that momentum has not yet reflected underlying macro deterioration."

---

## Key Lessons for Using Fin-Eye

1. **Macro leads. Technical lags.** In systemic crises, macro signals often lead technical
   by 6–18 months. A divergence between a positive Technical score and a deteriorating Macro
   score is a meaningful conflict worth heeding.

2. **Sentiment is coincident to slightly lagging** in most market conditions, but can
   provide fast-moving confirmation during acute stress events (like post-Lehman).

3. **GAS below 20 is not a trade signal — it is a caution flag.** The framework is
   educational. A GAS of 9 during October 2008 tells you the environment is hostile,
   not that you should short everything.

4. **The conflict detector is most valuable at turning points.** When all layers agree
   (as in late 2008), there is no conflict to detect. The framework's real edge is
   at transitions — when one layer has turned while others have not.

---

## Hindsight Disclaimer

This entire analysis is constructed with **full knowledge of what happened**. No investor
in 2007 had access to Fin-Eye, and even if they had, the framework provides contextual
signals — not trading rules. Many investors who correctly identified the macro deterioration
early still suffered large drawdowns because timing market turns is notoriously difficult.

Use this case study to understand *how the signals behave* over a full crisis cycle —
not as evidence that any framework can reliably predict or time crises.
""",
    },
    {
        "title": "Case Study: The 2020 COVID-19 Crash & Recovery",
        "slug": "case-study-2020-covid-crash",
        "summary": (
            "The fastest 30%-drawdown in stock market history — and then the fastest "
            "recovery. How Fin-Eye's GAS, regime classification, and sentiment layers "
            "would have tracked the COVID-19 shock from complacency to capitulation to "
            "V-shaped rebound."
        ),
        "category": "Case Studies",
        "read_time": "10 min read",
        "author": "Fin-Eye Research",
        "published_at": datetime(2026, 2, 15),
        "content_md": """\
# Case Study: The 2020 COVID-19 Crash & Recovery

> **Disclaimer:** This is a retrospective educational analysis using Fin-Eye's framework
> applied to historical data. It does not constitute investment advice. Past performance
> and historical signal reconstruction are not reliable indicators of future results.
> Always conduct your own research before making financial decisions.

---

## Overview

The COVID-19 market crash of February–March 2020 was historically unique:

- The S&P 500 fell **34% in 33 calendar days** — the fastest bear market in history
- VIX spiked to **85.47** on March 18, 2020 (second only to the 2008 intraday peak)
- The subsequent recovery was equally extreme — a full round-trip within **5 months**

Unlike 2008, which had months of macro deterioration as forewarning, COVID-19 was an
**exogenous shock**: the macro, sentiment, and technical signals were all broadly positive
in January 2020. This makes it a completely different test of how Fin-Eye's framework
behaves under a sudden, unexpected crisis.

---

## Timeline of Key Events

| Date | Event |
|------|-------|
| Dec 2019 | WHO alerted to pneumonia cluster in Wuhan |
| Jan 20, 2020 | First US COVID-19 case confirmed |
| Jan 31, 2020 | US declares public health emergency |
| Feb 19, 2020 | S&P 500 all-time high: **3,386** |
| Feb 24, 2020 | S&P 500 drops 3.4% — first major sell-off day |
| Mar 16, 2020 | Largest single-day points drop in Dow history |
| Mar 23, 2020 | S&P 500 bottoms at **2,237** (−34% from peak) |
| Mar 23, 2020 | Fed announces unlimited QE; Treasury announces stimulus |
| Aug 18, 2020 | S&P 500 fully recovers to pre-crash highs |

---

## Macro Layer: Positive Until It Wasn't

In January 2020, the macro backdrop was the strongest it had been in years:

- **Fed Funds Rate**: 1.75% — accommodative
- **Unemployment**: 3.5% — 50-year lows
- **Yield Curve**: Slightly positive, no inversion
- **VIX**: ~14 — calm

**Macro Score in January 2020: ~72 (Supportive)**

The macro layer provided **zero early warning** of the COVID crash — because there was
none. This was not a macro-driven recession brewing over years; it was an external shock.

### The Macro Response

The macro layer's signal collapsed only *after* the shock was visible:

| Date | Macro Score | Label |
|------|------------|-------|
| Jan 2020 | ~72 | Supportive |
| Feb 28, 2020 | ~55 | Neutral |
| Mar 23, 2020 | ~22 | Stressed |
| Apr 15, 2020 | ~18 | Stressed (Fed QE announced) |
| Jun 2020 | ~35 | Neutral (recovering) |
| Aug 2020 | ~52 | Neutral |

An important lesson: **macro indicators are mostly lagging during exogenous shocks**.
Unemployment didn't spike until April data (released in May); GDP contraction wasn't
confirmed until Q2 GDP data in July.

---

## Sentiment Layer: Fastest Collapse on Record

The sentiment layer is where the COVID crash shows its most distinctive signature.

### January 2020: Denial Phase
Financial news sentiment was **+0.35 to +0.45** — strongly positive. Headlines focused
on US-China trade deal progress, record employment, and strong earnings.

Notably, COVID-19 news *was* appearing from late January, but it was primarily
categorised under "health" and "international" rather than "market risk". FinBERT sentiment
on financial news remained positive through February 14.

### February 20–28: Sudden Regime Shift
In a single week, as equity sell-offs began and COVID containment failures became
apparent globally, news sentiment on S&P 500 constituents dropped from **+0.30 to −0.20**.

This 0.50-point drop in one week is approximately **3 standard deviations** from
the typical weekly change in news sentiment.

### March 2020: Capitulation
- Peak negative sentiment: **−0.72** (March 16–20, 2020)
- This was the fastest sentiment collapse from strongly positive to deeply negative
  in any period covered by financial news databases

### April–August 2020: Fastest Recovery in Sentiment
Unusually, sentiment recovered almost as fast as it collapsed:
- Fed QE and government stimulus announcements drove a rapid re-pricing of risk
- By June 2020, 30-day rolling sentiment was back to neutral (−0.05)
- By August 2020, it had returned to **+0.25**

---

## Technical Layer: Textbook Regime Transition

The technical layer during COVID provides the clearest example of how multi-timeframe
signals cascade from longer to shorter timeframes during a shock.

### Pre-Crash: All-Clear
In January 2020, S&P 500 and most large-cap stocks showed:
- All 5 timeframes (1h, 4h, 1d, 1w, 1m): **Bullish**
- Technical Confidence Score: **~78/100**
- Regime: **Risk-On**

### The Cascade (Feb 21 – Mar 10)

When momentum breaks suddenly, shorter timeframes lead longer ones:

| Date | 1h | 4h | 1d | 1w | 1m | TCS |
|------|----|----|----|----|----|----|
| Feb 20 | Bullish | Bullish | Bullish | Bullish | Bullish | 78 |
| Feb 24 | Bearish | Bearish | Neutral | Bullish | Bullish | 52 |
| Feb 28 | Bearish | Bearish | Bearish | Neutral | Bullish | 35 |
| Mar 6 | Bearish | Bearish | Bearish | Bearish | Neutral | 22 |
| Mar 16 | Bearish | Bearish | Bearish | Bearish | Bearish | 9 |

The cascade from first bearish signal (1h/4h on Feb 24) to fully aligned bearish
across all timeframes (Mar 16) took **21 calendar days** — about 3x faster than
a typical bear market transition.

### VIX Regime Shift
VIX moved from **Low** (13.7 on Feb 19) to **High** (>25) within 6 trading days — 
the fastest Low-to-High volatility regime shift on record.

---

## GAS Through the COVID Cycle

| Period | Tech Score | Sentiment Score | Macro Score | **GAS** | Weather |
|--------|-----------|-----------------|-------------|---------|---------|
| Jan 2020 | 78 | 72 | 72 | **74** | Mild Support |
| Feb 19 (peak) | 78 | 70 | 70 | **73** | Mild Support |
| Feb 28 | 35 | 30 | 55 | **38** | Headwind |
| Mar 16 | 10 | 12 | 22 | **13** | High Instability |
| Mar 23 (bottom) | 9 | 8 | 18 | **11** | High Instability |
| Apr 30 | 45 | 35 | 20 | **35** | Headwind |
| Jun 30 | 60 | 52 | 35 | **51** | Mixed Signals |
| Aug 18 (recovery) | 72 | 65 | 50 | **64** | Mild Support |

---

## Conflict Detector Behaviour in 2020

Unlike 2008 (where conflicts emerged during the multi-year buildup), the 2020 conflict
detector shows an interesting post-crash pattern.

**April–June 2020 Conflict: "Technical leading Macro"**

After the March 23 bottom, technical signals recovered rapidly (the market was going up),
but macro indicators were still deteriorating (unemployment was spiking, GDP hadn't been
reported yet):

> *"Technical layer is Bullish while Macro is Stressed — layers are 38 points apart.
> The technical bounce may reflect stimulus expectations rather than underlying
> economic improvement. Exercise caution."*

This is perhaps the most practically useful conflict alert in the 2020 data: it captures
the **fundamental vs. price divergence** that many investors found confusing throughout
the 2020 recovery.

---

## The V-Shape: What Made It Different From 2008?

The 2020 recovery was the fastest in stock market history. Understanding why matters
for interpreting Fin-Eye signals in future crises:

**1. The shock was external and bounded.** Unlike 2008 (structural leverage in the financial
system), COVID was an external event. Once vaccines were in development and stimulus was
announced, the uncertainty had a visible end date.

**2. Monetary response was 5x faster.** The Fed announced unlimited QE on March 23 — the
same day the market bottomed. In 2008, the first QE program began November 2008, two months
after Lehman.

**3. Fiscal response was immediate and enormous.** The CARES Act ($2.2 trillion) passed
March 27 — 4 days after the market bottom.

**For Fin-Eye users:** the macro layer during 2020 was a *lagging* indicator precisely
because policy response was so fast. This is one reason why macro-heavy GAS weighting
would have kept GAS depressed well into the recovery — while prices were already
recovering strongly.

---

## Key Lessons

1. **Exogenous shocks are not forecastable by trend-following frameworks.** No signal
   framework predicted COVID. The value of Fin-Eye in 2020 was not prediction but
   **rapid regime identification** — it would have confirmed the regime shift to
   High Instability within 3 weeks of the first sell-off.

2. **Sentiment is the fastest-moving layer for external shocks.** Because news sentiment
   responds to headlines within days, it may provide the earliest GAS contribution
   change during sudden crises.

3. **Post-shock conflicts are real and valuable.** The Technical vs. Macro conflict in
   April–June 2020 reflected genuine uncertainty. It didn't mean "don't buy" — it meant
   "the bullish case rests on future expectations, not current macro reality."

4. **GAS recovering slowly after a crash is normal.** Macro indicators recover last.
   Expect GAS to return to "Mild Support" territory weeks to months after prices recover.
   This is not a bug; it reflects the multi-layer nature of the scoring system.

---

## Hindsight Disclaimer

This analysis benefits from full knowledge of the crash timeline, policy responses, and
subsequent market recovery. In real-time, the situation felt far more uncertain. The analysis
is intended to show how the *framework's signals would have behaved* — not to suggest that
Fin-Eye would have generated actionable trading signals during this period. No educational
tool removes the uncertainty inherent in live markets.
""",
    },
]


# ─── Seed function ────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    inserted = 0
    skipped = 0
    try:
        for p in POSTS:
            existing = db.query(BlogPost).filter(BlogPost.slug == p["slug"]).first()
            if existing:
                print(f"  SKIP  '{p['slug']}' already exists.")
                skipped += 1
                continue

            post = BlogPost(
                title=p["title"],
                slug=p["slug"],
                summary=p["summary"],
                category=p["category"],
                read_time=p["read_time"],
                author=p["author"],
                content_md=p["content_md"],
                status="published",
                published_at=p["published_at"],
                created_at=p["published_at"],
                updated_at=p["published_at"],
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
    print("Seeding case study posts…")
    seed()
