# Skill: Fintech Signal Interpretation
# When to load: When writing or reviewing code that touches macro scoring, regime labels,
#               technical indicators, or GAS thresholds. Essential for developers without
#               a finance background.

## Purpose
Explains the finance domain reasoning behind fin-eye's scoring decisions.
This prevents developers from "accidentally fixing" logic that is intentionally calibrated.

---

## The Yield Curve — Most Important Macro Signal

The yield curve plots interest rates across different bond maturities. Normally, longer-dated
bonds yield more than shorter-dated bonds (upward slope) because investors demand more
compensation for lending money for longer.

**10Y–2Y Spread:** The difference between 10-year and 2-year US Treasury yields.
- **Positive (normal):** Long rates > short rates. Economy is expected to grow. Healthy.
- **Flat (near zero):** Growth concerns, uncertainty.
- **Negative (inverted):** Short rates > long rates. This has preceded every US recession
  since 1955, typically by 6–18 months. The most reliable recession predictor available.

**Why the thresholds in `macro_scoring.py` are what they are:**
- `-0.5%` deep inversion = -20 points: This level of inversion has historically meant recession is nearly certain within 12 months
- `< 0` inversion = -12 points: Early warning signal — not guaranteed but historically significant
- `> 1.5%` steep = +7 points: Strong growth expectations priced into the curve

**Do not change these thresholds without understanding the historical context.**

---

## VIX — The Fear Gauge

VIX is the CBOE Volatility Index. It measures the market's expectation of 30-day volatility
in the S&P 500, derived from options prices.

| VIX Level | Market Interpretation |
|-----------|----------------------|
| < 12 | Extreme complacency — very low fear, markets are calm |
| 12–15 | Low volatility — normal calm conditions |
| 15–20 | Moderate — typical baseline |
| 20–30 | Elevated — increased uncertainty |
| 30–40 | High fear — significant market stress |
| > 40 | Extreme fear — crisis conditions (COVID crash hit ~85) |

**Counterintuitive fact:** Very low VIX (< 12) is not always positive. It can signal complacency
before a correction. That is why the macro scoring gives only +6 points for VIX < 12, while
VIX > 40 gives -15 points. Fear spikes are more impactful than calm.

---

## RSI — Relative Strength Index

RSI measures momentum on a 0–100 scale. It compares the magnitude of recent gains to losses.

- **RSI < 30:** Oversold — the stock has fallen quickly and may be due for a bounce
- **RSI > 70:** Overbought — the stock has risen quickly and may be due for a pullback
- **RSI ~50:** Neutral momentum

**Important:** RSI is a momentum indicator, not a fundamental one. An RSI of 20 does not
mean the stock is cheap — it means it has been falling. In a strong downtrend, RSI can
stay oversold for weeks. Never use RSI alone as a buy/sell signal.

In fin-eye's ML model, RSI is a feature input — the model learns how to weight it in
combination with other signals, which is more powerful than using it as a standalone threshold.

---

## MACD — Moving Average Convergence Divergence

MACD = EMA(12) − EMA(26). The signal line = EMA(9) of MACD. The histogram = MACD − signal.

- **MACD crossing above signal line:** Bullish momentum shift
- **MACD crossing below signal line:** Bearish momentum shift
- **Histogram above zero and growing:** Strengthening bullish momentum
- **Histogram above zero and shrinking:** Bullish momentum fading

In fin-eye, the ML model receives `macd` and `macd_hist` as features. The histogram is more
informative than the raw MACD value because it captures the rate of change in momentum.

---

## Bollinger Bands

Bollinger Bands are a volatility envelope: middle band = 20-day SMA, upper/lower bands = ±2 standard deviations.

- **BB Width (`bb_width`):** How wide the bands are. Narrow = low volatility (often precedes a big move). Wide = high volatility.
- **BB %B (`bb_pb`):** Where the current price sits within the bands. 0 = at lower band, 0.5 = at middle, 1 = at upper band. Values above 1 or below 0 mean the price has broken outside the bands.

In fin-eye, both `bb_width` and `bb_pb` are active ML features. The model uses them to understand both the current volatility regime and where price sits relative to recent history.

---

## Sharpe Ratio — Why √252

The Sharpe Ratio is: `mean_return / std_return × √252`

The `√252` annualizes the ratio (252 = trading days per year). This scaling makes Sharpe
ratios comparable across models trained on different timeframes.

**Interpretation:**
- Sharpe < 0: Strategy loses money on a risk-adjusted basis
- 0–0.5: Weak signal, not recommended for live trading
- 0.5–1.0: Acceptable — suitable for a component in a composite signal like GAS
- 1.0–2.0: Good — strong edge relative to risk taken
- > 2.0: Exceptional — verify for overfitting before trusting

Hedge funds typically target Sharpe > 1.0. A GAS component signal at Sharpe 0.5–0.8 is
reasonable given it is one of three inputs.

---

## Risk-On vs Risk-Off Regime

These terms describe the market environment:

- **Risk-On:** Investors are comfortable taking risk. They buy equities, high-yield bonds,
  emerging markets. Volatility is low. This is the environment where growth stocks outperform.
- **Risk-Off:** Investors flee to safety. They sell equities and buy US Treasuries, gold, USD.
  Volatility is elevated. Defensive stocks (utilities, healthcare) outperform.

In fin-eye, the regime is derived purely from the technical consensus score:
- Technical ≥ 60 → Risk-On
- Technical ≤ 40 → Risk-Off
- 41–59 → Transitional

This is a simplified definition. A more complete regime model would incorporate VIX levels,
credit spreads, and cross-asset flows. The current definition is intentional for its simplicity
and explainability to users — do not over-engineer it without a clear product reason.

---

## GAS Score — What It Is and Is Not

**What GAS is:**
A composite signal summarizing whether the macro environment, technical trend, and market
sentiment are aligned favorably for a stock at this moment.

**What GAS is NOT:**
- A price prediction (it does not say "AAPL will go up tomorrow")
- A recommendation (it is not financial advice)
- A precision instrument (a GAS of 62 vs 65 is not meaningfully different)

**Practical interpretation for users:**
- GAS 70+: Most signals are aligned positively — favorable environment
- GAS 40–70: Mixed signals — no clear edge in either direction
- GAS < 40: Multiple signals are negative — challenging environment

The weather labels (Strong Tailwind, Mixed Signals, etc.) are intentionally non-committal
for regulatory and liability reasons. Always ensure the risk disclaimer is visible alongside GAS scores.
