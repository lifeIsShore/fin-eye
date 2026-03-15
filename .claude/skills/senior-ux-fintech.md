# Skill: Senior UX — Fintech Dashboard
# When to load: Before designing any new dashboard component, user flow,
#               or data visualization in fin-eye.

## Core Principle: Progressive Disclosure
Never show everything at once. fin-eye's data is dense — users need to be guided
from summary → detail, not confronted with all data simultaneously.

Layer 1 (always visible): GAS score + weather label + regime
Layer 2 (on demand): Component breakdown (technical/sentiment/macro)
Layer 3 (collapsible): Detailed signals, indicator values, model metadata

## The "Aha Moment" Design Target
A user's aha moment in fin-eye is: "I see the GAS score change, I understand why it changed, and I understand what it means for my decision."

Design every component to support this sequence:
1. Show the change (number, direction arrow, sparkline)
2. Explain the change (what drove it)
3. Contextualize (is this historically unusual?)

## Score Display Conventions
- Always show score as a number (0–100) AND a label — never one without the other
- Add a direction indicator when showing historical comparison (↑↓ or color-coded delta)
- Confidence percentages should show a progress bar, not just a number
- Model name (XGBoost/Logistic/Prophet) should be visible in the technical detail panel — users deserve to know what generated the signal

## Tooltip / Explain Pattern
Every score, label, and indicator needs an [i] icon that explains:
- What this metric measures (1 sentence)
- What a high vs low value means (1 sentence each)
- How it affects GAS (1 sentence)

This is the #1 activation driver for new users. Non-negotiable on GAS, Technical Score, Macro Score, Sentiment Score, Regime, and VIX.

## Financial Data Trust Signals
Users of financial tools are skeptical. Build trust through:
- Data freshness timestamp on every widget ("Updated 4 min ago" with a colored dot)
- Source attribution on macro indicators ("VIX from FRED · VIXCLS")
- Model confidence shown alongside signals (not hidden)
- Graceful degradation messages when a feed is down ("Sentiment temporarily unavailable — GAS computed without sentiment layer")

## Information Architecture Rules
- Max 4–5 navigation items visible at top level — group the rest
- Current fin-eye has 19 nav items: must be grouped into 3–4 categories
- Breadcrumbs on all pages below the top level
- CMD+K search for power users (ticker search, page navigation)

## Color & Contrast
- Minimum 4.5:1 contrast ratio for all text (WCAG AA)
- `text-slate-500` on `bg-slate-900` fails this check — use `text-slate-300` minimum
- Never rely on color alone to communicate state — always pair with text label or icon

## Empty vs Loading vs Error States
These are three different states and must look different:
- Loading: skeleton that matches final content shape
- Empty: icon + message + CTA
- Error: icon + message + retry button + (optionally) last known data with staleness notice
