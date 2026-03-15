# Skill: External Data Reasonability
# When to load: Before writing any data ingestion code, before debugging a data feed,
#               when GAS scores look frozen or implausible.

## Purpose
Defines what "reasonable" means for each external data source in fin-eye.
Silent data failures are the hardest bugs to catch — this skill helps you know
what to look for.

---

## OHLCV Data (Yahoo Finance via yfinance)

### Known Limitations
- **4h interval does not exist natively in yfinance.** Must fetch 1h and resample. Passing `interval="4h"` silently returns empty data — always check `len(df) > 0` after fetch.
- **Max lookback for intraday:** 1h = 730 days, 4h = 730 days (resampled from 1h). Requesting "5y" for intraday silently returns nothing.
- **Adjusted vs unadjusted close:** yfinance returns adjusted close by default. Raw close and adjusted close diverge after stock splits and dividends. For ML training, always use the same close type consistently — mixing them creates artificial price jumps.
- **Timezone:** yfinance returns timezone-aware timestamps. Prophet requires tz-naive. Always call `.dt.tz_localize(None)` before passing to Prophet.

### Sanity Checks for OHLCV
- Single-bar price gap > 20%: almost always a corporate action (split, spin-off) or data error. Log and investigate before training.
- Volume = 0 for multiple consecutive bars: stock may have been halted, or the feed is broken. More than 3 consecutive zero-volume bars is a hard warning.
- OHLC ordering violation: `low > high` or `close > high` or `close < low` means corrupted data. Fail hard.
- Minimum bars for training: 200 (hard minimum), 300+ (recommended for stable estimates).

---

## Macro Data (FRED API)

### Release Frequency — Know This Before Checking Staleness

| Indicator | FRED Series | Release Frequency | Max Acceptable Staleness |
|-----------|-------------|-------------------|--------------------------|
| VIX | VIXCLS | Daily | 1 business day |
| Fed Funds Rate | FEDFUNDS | Monthly (FOMC meetings ~8/year) | 7 days |
| 10Y–2Y Yield Spread | T10Y2Y | Daily | 1 business day |
| CPI YoY | CPIAUCSL | Monthly | 35 days |
| Unemployment Rate | UNRATE | Monthly | 35 days |
| Nonfarm Payrolls | PAYEMS | Monthly (1st Friday of month) | 35 days |
| Industrial Production | INDPRO | Monthly | 35 days |
| NBER Recession Indicator | USREC | Lagged (declared months after) | N/A — always use latest |

### Key Points
- **FRED data is revised.** Initial NFP releases are often revised significantly in subsequent months. The model trains on whatever was in the DB at training time, which may not match what FRED shows today. This is expected behavior, not a bug.
- **VIX gaps on weekends:** FRED's VIXCLS has no weekend values. Forward-fill is correct for macro indicators — do not interpolate.
- **Yield spread can be negative:** An inverted yield curve (10Y < 2Y) produces a negative spread. This is valid data, not an error. The macro scoring engine handles this intentionally.
- **USREC lag:** NBER officially declares recessions months after they begin. A USREC value of 0 does not mean the economy is definitely healthy — it means no recession has been officially declared yet.

---

## Sentiment Data (FinBERT / News)

### What FinBERT Returns
FinBERT scores articles on a [-1, +1] scale: +1 = strongly positive financial sentiment, -1 = strongly negative. Neutral is near 0.

### Reasonability Checks
- **Score concentration:** If > 90% of articles over 7 days score the same direction (all positive or all negative), suspect the feed is broken or a single source is dominating. Real news is mixed.
- **Score extremes:** Scores consistently at ±0.9+ are unusual. Most financial news is nuanced and scores in the ±0.2–0.6 range. Very extreme scores suggest either genuinely exceptional news or a feed/model issue.
- **Zero articles for days:** If `news_data` returns 0 articles for a known large-cap stock over multiple days, the Finnhub API key may have hit its rate limit, or the feed connector is down. GAS will silently fall back to sentiment=50.0 in this case.
- **Source diversity:** The `news_source_diversity_30d` feature counts distinct news sources. For major stocks (AAPL, TSLA) this should be > 5 over 30 days. If it is 1, only one source is feeding in — confirm the news ingestion pipeline is healthy.

---

## Social Sentiment (Reddit, StockTwits)

### Reasonability Checks
- Reddit/StockTwits sentiment is noisier than news. Scores swinging ±0.5 day-over-day are normal during market events.
- Meme stock dynamics: For stocks like GME or AMC, social sentiment can be extremely positive even when the business fundamentals are poor. Social sentiment should never be used in isolation.
- These sources are currently stored separately and are NOT the primary GAS sentiment input (news is). Check `gas_precompute.py: _compute_sentiment_score()` to confirm what is actually being used.

---

## General Rules for Adding New Data Sources

1. **Always check for silent empty responses.** Log `len(result)` after every fetch. Never assume data is present.
2. **Document the release schedule.** If you add a new indicator, add it to the staleness table above and to `config.yaml`.
3. **Handle missing values with fallback, not zero.** Zero is a valid value for many indicators (e.g. yield spread = 0). Use `None` for missing and handle with forward-fill or the 50.0 fallback.
4. **Test on a ticker that is NOT AAPL.** Many data quality bugs only appear on less-covered stocks.
5. **Check timezone consistency.** All timestamps in fin-eye should be UTC. Convert at the ingestion point, not deep in the pipeline.
