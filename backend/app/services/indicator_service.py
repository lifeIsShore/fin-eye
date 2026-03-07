"""
app/services/indicator_service.py
─────────────────────────────────────────────────────────────────────────────
P3-ANALYTICS-01 — No-Code Indicator Builder: evaluation engine

Formula representation
──────────────────────
A formula is a JSON expression tree using a strict whitelist of nodes.
This guarantees safe sandboxed evaluation — no Python eval(), no exec().

Node types:
  { "type": "indicator", "fn": "RSI", "params": {"period": 14} }
  { "type": "indicator", "fn": "SMA", "params": {"period": 20} }
  { "type": "indicator", "fn": "EMA", "params": {"period": 20} }
  { "type": "indicator", "fn": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "output": "macd"|"signal"|"hist" }
  { "type": "indicator", "fn": "BB",   "params": {"period": 20, "std": 2.0}, "output": "upper"|"lower"|"mid"|"width"|"pb" }
  { "type": "indicator", "fn": "ATR",  "params": {"period": 14} }
  { "type": "indicator", "fn": "STOCH","params": {"k": 14, "d": 3}, "output": "k"|"d" }
  { "type": "indicator", "fn": "OBV",  "params": {} }
  { "type": "indicator", "fn": "ROC",  "params": {"period": 10} }
  { "type": "indicator", "fn": "CCI",  "params": {"period": 20} }
  { "type": "indicator", "fn": "VWAP", "params": {} }
  { "type": "indicator", "fn": "CLOSE","params": {} }
  { "type": "indicator", "fn": "VOLUME","params":{} }

  { "type": "binop", "op": "+"|"-"|"*"|"/"|">"|"<"|">="|"<=", "left": <node>, "right": <node> }
  { "type": "number", "value": 30.0 }
  { "type": "cross", "direction": "above"|"below", "fast": <node>, "slow": <node> }

Output
──────
`evaluate(formula, symbol, timeframe, periods)` returns a dict:
  {
    "dates":  ["2024-01-01", ...],
    "values": [42.3, null, ...],   # null where NaN (warm-up period)
    "type":   "continuous" | "signal",   # signal = 0/1 series
    "summary": { "min": .., "max": .., "mean": .., "current": .. }
  }

Signal series (from `cross` nodes) are 0.0/1.0 where 1.0 = cross event fired.
"""
from __future__ import annotations

import logging
import math
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Cache: (symbol, timeframe) → (ts, df) ────────────────────────────────────
_DATA_CACHE: Dict[str, tuple] = {}
_DATA_TTL = 900  # 15 min — matches GAS pre-compute cycle


# ── OHLCV loader ─────────────────────────────────────────────────────────────

def _load_ohlcv(symbol: str, timeframe: str = "1d", periods: int = 500) -> pd.DataFrame:
    """
    Fetch OHLCV data for a symbol. Cached 15 min.
    Returns DataFrame with columns: open, high, low, close, volume; DatetimeIndex.
    """
    cache_key = f"{symbol}:{timeframe}:{periods}"
    now = time.time()
    if cache_key in _DATA_CACHE:
        ts, df = _DATA_CACHE[cache_key]
        if now - ts < _DATA_TTL:
            return df

    try:
        import yfinance as yf
        period_map = {
            "1d": "2y",
            "1h": "730d",
            "1wk": "10y",
            "1mo": "20y",
        }
        yf_period = period_map.get(timeframe, "2y")
        ticker = yf.Ticker(symbol.upper())
        df = ticker.history(period=yf_period, interval=timeframe, auto_adjust=True)

        if df.empty:
            logger.warning("No OHLCV data returned for %s %s", symbol, timeframe)
            return pd.DataFrame()

        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)

        # Keep only the last `periods` rows so output is manageable
        if len(df) > periods:
            df = df.iloc[-periods:]

        _DATA_CACHE[cache_key] = (now, df)
        logger.info("Loaded %d bars for %s %s", len(df), symbol, timeframe)
        return df
    except Exception as exc:
        logger.error("OHLCV load failed for %s %s: %s", symbol, timeframe, exc)
        return pd.DataFrame()


# ── Indicator computations ────────────────────────────────────────────────────

def _sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(period).mean()


def _ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
          ) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_f = close.ewm(span=fast, adjust=False).mean()
    ema_s = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_f - ema_s
    sig_line  = macd_line.ewm(span=signal, adjust=False).mean()
    hist      = macd_line - sig_line
    return macd_line, sig_line, hist


def _bb(close: pd.Series, period: int = 20, std: float = 2.0
        ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    mid   = close.rolling(period).mean()
    s     = close.rolling(period).std()
    upper = mid + s * std
    lower = mid - s * std
    width = (upper - lower) / mid.replace(0, np.nan)
    pb    = (close - lower) / (upper - lower).replace(0, np.nan)
    return upper, lower, mid, width, pb


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _stoch(high: pd.Series, low: pd.Series, close: pd.Series, k: int = 14, d: int = 3
           ) -> tuple[pd.Series, pd.Series]:
    lo_k = low.rolling(k).min()
    hi_k = high.rolling(k).max()
    k_pct = 100 * (close - lo_k) / (hi_k - lo_k).replace(0, np.nan)
    d_pct = k_pct.rolling(d).mean()
    return k_pct, d_pct


def _obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    sign = np.sign(close.diff().fillna(0))
    return (sign * volume).cumsum()


def _roc(close: pd.Series, period: int = 10) -> pd.Series:
    return close.pct_change(period) * 100


def _cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    tp = (high + low + close) / 3
    sma_tp = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    return (tp - sma_tp) / (0.015 * mad.replace(0, np.nan))


def _vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    tp = (high + low + close) / 3
    # Rolling VWAP over a 20-period window (no session boundary info available)
    cumtp_vol = (tp * volume).rolling(20).sum()
    cumvol    = volume.rolling(20).sum()
    return cumtp_vol / cumvol.replace(0, np.nan)


# ── Expression tree evaluator ─────────────────────────────────────────────────

def _eval_node(node: Dict[str, Any], df: pd.DataFrame) -> pd.Series:
    """
    Recursively evaluate a formula node against a OHLCV DataFrame.
    Returns a pd.Series aligned to df.index.
    """
    ntype = node.get("type")

    # ── Numeric literal ───────────────────────────────────────────────────
    if ntype == "number":
        val = float(node["value"])
        return pd.Series(val, index=df.index)

    # ── Indicator node ────────────────────────────────────────────────────
    if ntype == "indicator":
        fn     = node["fn"].upper()
        params = node.get("params", {})
        out    = node.get("output", "")
        c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

        if fn == "CLOSE":  return c.copy()
        if fn == "VOLUME": return v.copy()

        if fn == "SMA":
            period = int(params.get("period", 20))
            return _sma(c, period)

        if fn == "EMA":
            period = int(params.get("period", 20))
            return _ema(c, period)

        if fn == "RSI":
            period = int(params.get("period", 14))
            return _rsi(c, period)

        if fn == "MACD":
            fast   = int(params.get("fast", 12))
            slow   = int(params.get("slow", 26))
            signal = int(params.get("signal", 9))
            macd, sig, hist = _macd(c, fast, slow, signal)
            return {"macd": macd, "signal": sig, "hist": hist}.get(out, macd)

        if fn == "BB":
            period = int(params.get("period", 20))
            std    = float(params.get("std", 2.0))
            upper, lower, mid, width, pb = _bb(c, period, std)
            return {"upper": upper, "lower": lower, "mid": mid, "width": width, "pb": pb}.get(out, mid)

        if fn == "ATR":
            period = int(params.get("period", 14))
            return _atr(h, l, c, period)

        if fn == "STOCH":
            k = int(params.get("k", 14))
            d = int(params.get("d", 3))
            k_s, d_s = _stoch(h, l, c, k, d)
            return {"k": k_s, "d": d_s}.get(out, k_s)

        if fn == "OBV":
            return _obv(c, v)

        if fn == "ROC":
            period = int(params.get("period", 10))
            return _roc(c, period)

        if fn == "CCI":
            period = int(params.get("period", 20))
            return _cci(h, l, c, period)

        if fn == "VWAP":
            return _vwap(h, l, c, v)

        raise ValueError(f"Unknown indicator function: {fn}")

    # ── Binary operation ──────────────────────────────────────────────────
    if ntype == "binop":
        op  = node["op"]
        lhs = _eval_node(node["left"],  df)
        rhs = _eval_node(node["right"], df)
        ops = {
            "+": lhs + rhs, "-": lhs - rhs,
            "*": lhs * rhs, "/": lhs / rhs.replace(0, np.nan),
            ">": (lhs > rhs).astype(float),
            "<": (lhs < rhs).astype(float),
            ">=": (lhs >= rhs).astype(float),
            "<=": (lhs <= rhs).astype(float),
        }
        if op not in ops:
            raise ValueError(f"Unknown binary operator: {op}")
        return ops[op]

    # ── Cross detection ───────────────────────────────────────────────────
    if ntype == "cross":
        direction = node.get("direction", "above")
        fast = _eval_node(node["fast"], df)
        slow = _eval_node(node["slow"], df)
        if direction == "above":
            # 1 on the bar where fast crosses above slow
            was_below = (fast.shift(1) <= slow.shift(1))
            is_above  = (fast > slow)
            return (was_below & is_above).astype(float)
        else:
            was_above = (fast.shift(1) >= slow.shift(1))
            is_below  = (fast < slow)
            return (was_above & is_below).astype(float)

    raise ValueError(f"Unknown node type: {ntype}")


# ── Public API ────────────────────────────────────────────────────────────────

def evaluate(
    formula: Dict[str, Any],
    symbol: str,
    timeframe: str = "1d",
    periods: int = 300,
) -> Dict[str, Any]:
    """
    Evaluate a formula against OHLCV data for a symbol.

    Returns:
      {
        "dates":   [str, ...],
        "values":  [float|None, ...],
        "type":    "continuous" | "signal",
        "summary": {"min": float, "max": float, "mean": float, "current": float|None}
      }
    """
    df = _load_ohlcv(symbol, timeframe, periods + 50)   # fetch extra for warm-up
    if df.empty:
        raise ValueError(f"No market data available for {symbol} {timeframe}")

    series = _eval_node(formula, df)

    # Detect signal series (only 0.0 / 1.0 / NaN)
    unique_vals = series.dropna().unique()
    is_signal = set(float(v) for v in unique_vals).issubset({0.0, 1.0})
    series_type = "signal" if is_signal else "continuous"

    # Return only the last `periods` data points (after warm-up)
    series = series.iloc[-periods:]

    dates  = [d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
              for d in series.index]
    raw    = series.tolist()
    values = [None if (v is None or (isinstance(v, float) and math.isnan(v))) else round(float(v), 6)
              for v in raw]

    clean_vals = [v for v in values if v is not None]
    summary = {
        "min":     round(min(clean_vals), 4) if clean_vals else None,
        "max":     round(max(clean_vals), 4) if clean_vals else None,
        "mean":    round(sum(clean_vals) / len(clean_vals), 4) if clean_vals else None,
        "current": values[-1] if values else None,
    }

    return {
        "dates":   dates,
        "values":  values,
        "type":    series_type,
        "summary": summary,
    }


# ── Formula validator ─────────────────────────────────────────────────────────

VALID_FNS = {
    "SMA", "EMA", "RSI", "MACD", "BB", "ATR",
    "STOCH", "OBV", "ROC", "CCI", "VWAP", "CLOSE", "VOLUME",
}
VALID_OPS  = {"+", "-", "*", "/", ">", "<", ">=", "<="}
VALID_TYPES = {"indicator", "binop", "number", "cross"}


def validate_formula(node: Dict[str, Any], depth: int = 0) -> list[str]:
    """
    Walk the formula tree and return a list of validation error messages.
    Empty list = valid.
    """
    errors: list[str] = []
    if depth > 10:
        errors.append("Formula tree too deep (max depth 10)")
        return errors

    ntype = node.get("type")
    if ntype not in VALID_TYPES:
        errors.append(f"Unknown node type: {ntype!r}")
        return errors

    if ntype == "number":
        try:
            float(node["value"])
        except (KeyError, TypeError, ValueError):
            errors.append("number node missing or invalid 'value' field")

    elif ntype == "indicator":
        fn = str(node.get("fn", "")).upper()
        if fn not in VALID_FNS:
            errors.append(f"Unknown indicator function: {fn!r}")
        params = node.get("params", {})
        for k, v in params.items():
            try:
                float(v)
            except (TypeError, ValueError):
                errors.append(f"Indicator param {k!r} is not numeric: {v!r}")

    elif ntype == "binop":
        op = node.get("op")
        if op not in VALID_OPS:
            errors.append(f"Unknown operator: {op!r}")
        for side in ("left", "right"):
            child = node.get(side)
            if child is None:
                errors.append(f"binop missing '{side}' child")
            else:
                errors.extend(validate_formula(child, depth + 1))

    elif ntype == "cross":
        if node.get("direction") not in ("above", "below"):
            errors.append("cross node 'direction' must be 'above' or 'below'")
        for side in ("fast", "slow"):
            child = node.get(side)
            if child is None:
                errors.append(f"cross missing '{side}' child")
            else:
                errors.extend(validate_formula(child, depth + 1))

    return errors
