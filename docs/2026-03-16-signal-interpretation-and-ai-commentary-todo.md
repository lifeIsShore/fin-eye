# Signal Interpretation & AI Commentary — Structured TODO
> **Created:** 2026-03-16
> **Status:** 📋 Design-approved ideas, ready to implement in phases
> **Research basis:** Fintech UX best practices 2025/2026 + regulatory analysis

---

## 🧠 Background & Problem Statement

The GAS score panel currently shows:
> *"The GAS is a composite signal... A score above 60 indicates bullish alignment; below 40 signals bearish pressure."*

This is accurate but **passive** — it describes what the number is, not what it means for the user right now. Users (especially non-technical ones) are left asking: *"OK, 37/100. So what do I do?"*

The instinct to answer that question directly (buy/sell/hold) runs into a hard wall: **that is investment advice**, which is a regulated activity in most jurisdictions. Fin-Eye must never cross that line.

The good news: there is a large, well-established design space between *"here is a number"* and *"buy this stock"* — and the best fintech tools (Koyfin, Danelfin, TipRanks, Simply Wall St.) all operate comfortably in it.

---

## ✅ Part 1 — Signal Interpretation Layer (Safe to Build Now)

### What This Is
Contextual, colour-coded plain-English interpretation of score ranges — **describing market conditions**, not recommending actions. The framing is always *"the signal environment looks like X"*, never *"you should do Y"*.

### The Legal Safe Zone
The line is between:
- ✅ **Safe:** "Signals are broadly bearish — the data environment is not supportive right now"
- ✅ **Safe:** "Mixed signals — the picture is unclear, caution is warranted"
- ✅ **Safe:** "Strong tailwind — conditions are aligned in a bullish direction"
- ❌ **Not safe:** "Buy", "Sell", "Reduce your position", "This is a good entry point"

This is the same framing used by:
- **TradingView** (Technical Rating: Strong Buy → Strong Sell — purely signal-based, no personal advice)
- **Danelfin** (AI Score 1–10 with "Risk/Reward" interpretation)
- **Simply Wall St.** (Snowflake scores with narrative — "This company has strong fundamentals")
- **Koyfin** (Signal strength labels without trade recommendations)

### Implementation: Score Interpretation Labels

Each score range gets a **label**, a **colour**, and a **1-sentence plain-English interpretation** — displayed directly on the score panel, no click required.

#### GAS Score Interpretation Table

| Range | Label | Colour | Plain English |
|-------|-------|--------|---------------|
| 80–100 | Strong Tailwind | Emerald | All three layers (technical, sentiment, macro) are aligned in a bullish direction. The data environment is broadly supportive. |
| 60–79 | Mild Support | Sky | Most signals lean positive, with some mixed readings. Conditions are moderately supportive. |
| 40–59 | Mixed Signals | Amber | Technical, sentiment, and macro signals disagree. The picture is unclear — elevated uncertainty. |
| 20–39 | Headwind | Rose/Orange | Signals lean bearish across multiple layers. The data environment is not supportive at this time. |
| 0–19 | High Instability | Red | Strong bearish alignment across all layers. Conditions are unfavourable and volatile. |

#### Technical Score Interpretation

| Range | Label | Colour | Plain English |
|-------|-------|--------|---------------|
| ≥ 80 | Strong Bullish Momentum | Emerald | Most timeframes agree: models see upward pressure. |
| 60–79 | Bullish Lean | Sky | Majority of timeframes lean bullish, some disagreement. |
| 40–59 | No Clear Direction | Amber | Timeframes are split — models see no strong edge in either direction. |
| 20–39 | Bearish Lean | Orange | Majority of timeframes lean bearish. |
| < 20 | Strong Bearish Momentum | Rose | Most timeframes agree: models see downward pressure. |

#### Sentiment Score Interpretation

| Range | Label | Colour | Plain English |
|-------|-------|--------|---------------|
| ≥ 70 | Very Positive Coverage | Emerald | News coverage over the past 30 days has been predominantly positive. |
| 55–69 | Mildly Positive | Sky | Slightly more positive than negative coverage. |
| 45–54 | Neutral | Amber | Coverage is broadly balanced with no strong directional lean. |
| 30–44 | Mildly Negative | Orange | News coverage leans negative over the past 30 days. |
| < 30 | Strongly Negative | Rose | News coverage has been predominantly negative. |

#### Macro Score Interpretation

Already implemented with labels (Supportive / Neutral / Stressed) — extend with colour and sub-label:

| Range | Label | Colour | Sub-label |
|-------|-------|--------|-----------|
| ≥ 70 | Supportive | Emerald | Macro environment is broadly favourable for risk assets. |
| 40–69 | Neutral | Amber | Mixed macro signals — neither clearly supportive nor restrictive. |
| < 40 | Stressed | Rose | Macro indicators are unfavourable. Conditions may add headwinds. |

### Implementation Location
- `ScoreExplainPanel.tsx` — add interpretation label + colour below the headline score
- `page.tsx` GAS widget header — show label inline next to the score (already partially done)
- `MarketWeatherWidget.tsx` — already has weather labels, extend to show interpretation text

### Effort Estimate: 2–3 hours

---

## 🟡 Part 2 — Condition Guidance (Safe With Caveats)

### What This Is
*Environment-based* guidance — describing what the **market condition** typically implies, framed as general market behaviour, not personalised advice. This is what Investopedia, Bloomberg, and most major financial media do every day.

### The Key Framing Rule
Always frame as **"in this type of environment, [market behaviour X is historically common]"** — never as **"you should [action]"**.

### Examples of Safe Condition Guidance

```
GAS 37 / Headwind:
"Historically, a sub-40 GAS reading has coincided with elevated volatility
and choppy price action. Signals are not aligned — conditions like these
often reward patience over activity."

GAS 72 / Mild Support:
"Signals are broadly aligned in a bullish direction. In historically similar
environments, momentum has tended to persist in the near term. Caution is
still warranted — signals can shift quickly."

GAS 18 / High Instability:
"All layers are bearish simultaneously. Historically, this combination
precedes continued downward pressure rather than reversals. Low-confidence
environments like this carry elevated risk."
```

### What To Be Careful About
- ❌ Never say "this is a good time to buy/sell"
- ❌ Never say "hold your position" or "reduce exposure" — these are personal advice
- ✅ Say "signals suggest [condition]" or "historically, this environment has been associated with [outcome]"
- ✅ Always accompany with the disclaimer: "This is educational analysis, not investment advice."

### Implementation Location
- `ScoreExplainPanel.tsx` — add a "Market Environment" section below the score bar
- Text is static/rule-based (no AI required for Phase 1)

### Effort Estimate: 2 hours

---

## 🔴 Part 3 — Portfolio-Aware AI Commentary (Future — Requires Opt-In)

### What This Is
This is the grey area you identified — giving contextual commentary that is aware of what the user holds and at what price. This has real UX value but carries regulatory risk if not handled carefully.

### Why This Is Technically Investment Advice
Under most financial regulations (MiFID II in EU, SEC regulations in US), advice that:
1. References a specific financial instrument **AND**
2. Considers a user's personal situation (holdings, entry price) **AND**
3. Recommends a specific action

...is classified as **personalised investment advice**, which requires a financial adviser licence.

### How To Do It Safely (the "robo-adviser framing")

The key distinction regulators draw is between:
- **General information:** "BTC-USD has a bearish GAS score of 18" ✅
- **Personalised advice:** "You should sell your BTC-USD position" ❌
- **Portfolio-aware context** (the grey zone): "Based on your tracked entry of $85,000 and a current bearish GAS reading, the signal environment has shifted since your noted entry" — this is borderline, but defensible if:
  - User explicitly opted in to "Portfolio Insight Mode"
  - All output is accompanied by prominent disclaimer
  - Output is framed as **context**, not **recommendation**
  - No specific action word ("sell", "buy", "reduce", "increase") appears

### Proposed Architecture

#### Phase 3A — Portfolio Entry Tracking (No AI needed yet)
- Add `entry_price` and `entry_date` fields to the portfolio/watchlist model
- When a tracked symbol has entry data, show a "Since your entry" card:
  - GAS at entry vs GAS now (signal environment change)
  - Technical signal at entry vs now
  - Sentiment direction since entry
- **No recommendation language** — purely shows signal drift

#### Phase 3B — AI Commentary (Opt-in, Settings-gated)
- Add a toggle in Settings: **"Enable AI Signal Commentary"** (off by default)
- When enabled, a commentary card appears below the GAS score
- The AI (local model or Claude API) generates a 2-3 sentence contextual paragraph using:
  - Current GAS score + label
  - Trend direction (improving/declining over last 7 days)
  - Portfolio entry data (if available)
  - Macro regime
- **Strictly prohibited output words for the AI system prompt:** buy, sell, purchase, exit, reduce, increase, enter, short, long, trade, invest
- **Required framing words:** "signal environment", "conditions suggest", "historically associated with", "context for consideration"
- Every AI output is tagged: *"AI-generated signal interpretation. Not investment advice. Past signals do not predict future performance."*

#### Phase 3C — Statistical Commentary (Safer than AI)
Instead of LLM generation, use pre-written templates parameterised by score ranges:

```python
TEMPLATES = {
  "bearish_entry_above": (
    "Your tracked entry ({entry_price}) was made when conditions were more favourable "
    "(GAS {entry_gas}). The signal environment has since shifted to {current_label} ({current_gas}). "
    "This is a data point, not a recommendation — always conduct your own research."
  ),
  "bullish_continuation": (
    "The signal environment around {symbol} has remained {label} for {days} days. "
    "Historically, sustained high-GAS periods have been associated with continued momentum, "
    "though signals can reverse quickly."
  ),
  ...
}
```

This is the **recommended starting point** — it avoids LLM hallucination risk and is easier to audit for compliance.

### Settings Page Implementation

```
Settings > Analysis Preferences
  [Toggle] Portfolio-Aware Signal Context
  When enabled, Fin-Eye will show how the signal environment has changed
  relative to your tracked entry prices. This is educational context only —
  not investment advice.

  [Toggle] AI Signal Commentary  (requires Portfolio-Aware Context to be ON)
  When enabled, an AI-generated paragraph summarises current signal conditions
  in plain language. Output is always statistical/educational in nature.
  Never constitutes investment advice.
```

### Effort Estimate: Phase 3A = 4h, Phase 3B = 8h, Phase 3C = 3h

---

## 📋 Implementation Order (Recommended)

| Phase | What | Risk | Effort | Prerequisite |
|-------|------|------|--------|--------------|
| 1 | Score interpretation labels + colours on all panels | None | 2–3h | None |
| 2 | Condition guidance paragraphs (rule-based, no AI) | Low | 2h | Phase 1 |
| 3A | Portfolio entry tracking (no commentary yet) | None | 4h | Portfolio page |
| 3B-stat | Statistical commentary templates (opt-in) | Low | 3h | 3A |
| 3B-ai | AI commentary via Claude/local model (opt-in) | Medium | 8h | 3A + Settings toggle |

---

## ⚖️ Regulatory Notes

- **EU (MiFID II):** Signal tools that describe market conditions are generally not regulated as investment advice if they are not personalised to the user's financial situation. Once you introduce portfolio entry data + action language, you are in regulated territory.
- **UK (FCA):** Same principle — "signal tools" are fine; "personalised recommendations" require authorisation.
- **US (SEC/FINRA):** Investment advice requires registration unless it falls under a recognised exemption. Educational tools that describe signals are generally not affected.
- **Safe harbour:** Always display the disclaimer. Gate portfolio-aware features behind an explicit opt-in that shows the user the disclaimer before activation. Never use action words in AI output.

---

## 🎨 UI Design Notes for Phase 1 & 2

### Score Panel Anatomy (updated)
```
┌─────────────────────────────────────────────┐
│  SCORE BREAKDOWN                             │
│  Global Alignment Score (GAS)                │
│                                              │
│  37  / 100   [Headwind ●]                    │  ← colour-coded label
│  ████░░░░░░░░░░░  (progress bar)             │
│                                              │
│  Signals are not aligned — conditions are    │  ← condition guidance
│  not broadly supportive at this time.        │    (amber/rose text)
│  Patience is historically rewarded in        │
│  low-GAS environments like this.             │
│                                              │
│  ─────────────────────────────────────────  │
│  Signal Breakdown                            │
│  [Technical 40%] [Sentiment 30%] [Macro 30%] │
└─────────────────────────────────────────────┘
```

### Colour System for Interpretation Labels

| Score Range | Badge BG | Badge Text | Body Text |
|------------|----------|------------|-----------|
| 80–100 | `bg-emerald-950/40 border-emerald-700/50` | `text-emerald-400` | `text-emerald-300` |
| 60–79 | `bg-sky-950/40 border-sky-700/50` | `text-sky-400` | `text-sky-300` |
| 40–59 | `bg-amber-950/40 border-amber-700/50` | `text-amber-400` | `text-amber-300` |
| 20–39 | `bg-orange-950/40 border-orange-700/50` | `text-orange-400` | `text-orange-300` |
| 0–19 | `bg-rose-950/40 border-rose-700/50` | `text-rose-400` | `text-rose-300` |

---

*Last updated: 2026-03-16*
*Author: Senior Dev + Product*
