import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, Any, Tuple, Optional

from app.schemas.backtest_models import (
    BacktestRequest, BacktestResponse, BacktestStats, EquityPoint,
    TradeRecord, WalkForwardRequest, WalkForwardFold, WalkForwardResponse,
)
from app.services.market_data import OHLCVFetcher

# Sprint 25 — supported benchmark tickers and their display labels
BENCHMARK_LABELS: dict[str, str] = {
    "SPY":     "S&P 500 (SPY)",
    "QQQ":     "Nasdaq 100 (QQQ)",
    "BTC-USD": "Bitcoin (BTC-USD)",
    "GLD":     "Gold (GLD)",
}

logger = logging.getLogger(__name__)


class BacktestingEngine:
    """Core engine for running historical backtests on different strategies."""

    SUPPORTED_STRATEGIES = ["momentum", "mean_reversion", "macro_responsive"]

    def __init__(self, request: BacktestRequest):
        self.request = request
        self.symbol = request.symbol
        self.strategy = request.strategy
        self.params = request.parameters
        self.initial_capital = request.initial_capital
        self.slippage = request.slippage_pct

    def run(self) -> BacktestResponse:
        """Runs the backtest based on the configured request and returns results."""
        if self.strategy not in self.SUPPORTED_STRATEGIES:
            raise ValueError(
                f"Strategy '{self.strategy}' is not supported. "
                f"Choose from: {self.SUPPORTED_STRATEGIES}"
            )

        historical_data = OHLCVFetcher.fetch_historical_data(
            self.symbol, period="5y", interval="1d"
        )

        if not historical_data:
            raise ValueError(f"Could not fetch data for symbol {self.symbol}")

        df = pd.DataFrame([
            {
                "date": row.timestamp.date(),
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume,
            }
            for row in historical_data
        ]).set_index("date")
        df.sort_index(inplace=True)

        if self.request.start_date:
            try:
                start_dt = datetime.strptime(self.request.start_date, "%Y-%m-%d").date()
                df = df[df.index >= start_dt]
            except ValueError:
                from fastapi import HTTPException  # noqa: PLC0415
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid start_date '{self.request.start_date}'. Expected YYYY-MM-DD."
                )
        else:
            start_dt = None
        if self.request.end_date:
            try:
                end_dt = datetime.strptime(self.request.end_date, "%Y-%m-%d").date()
                df = df[df.index <= end_dt]
            except ValueError:
                from fastapi import HTTPException  # noqa: PLC0415
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid end_date '{self.request.end_date}'. Expected YYYY-MM-DD."
                )
        else:
            end_dt = None
        if start_dt and end_dt and start_dt >= end_dt:
            from fastapi import HTTPException  # noqa: PLC0415
            raise HTTPException(
                status_code=422,
                detail="start_date must be before end_date."
            )

        if len(df) < 50:
            raise ValueError(
                f"Not enough data points ({len(df)}) for {self.symbol} after filtering "
                "to run a reliable backtest."
            )

        if self.strategy == "momentum":
            df_res, stats_dict = self._run_momentum_strategy(df)
        elif self.strategy == "mean_reversion":
            df_res, stats_dict = self._run_mean_reversion_strategy(df)
        elif self.strategy == "macro_responsive":
            df_res, stats_dict = self._run_macro_responsive_strategy(df)
        else:
            raise ValueError(f"Strategy {self.strategy} is not fully implemented.")

        stats = BacktestStats(**stats_dict)

        equity_curve = [
            EquityPoint(
                date=str(idx),
                equity=row["equity"],
                benchmark_equity=(
                    row["benchmark_equity"]
                    if pd.notna(row.get("benchmark_equity"))
                    else None
                ),
            )
            for idx, row in df_res.iterrows()
            if pd.notna(row["equity"])
        ]

        # ── Sprint 25: custom benchmark overlay ──────────────────────────────
        benchmark_ticker = (self.request.benchmark or "").strip().upper()
        benchmark_label  = "Buy & Hold"
        if benchmark_ticker and benchmark_ticker != self.symbol:
            try:
                bm_data = OHLCVFetcher.fetch_historical_data(
                    benchmark_ticker, period="5y", interval="1d"
                )
                if bm_data:
                    df_bm = pd.DataFrame([
                        {"date": r.timestamp.date(), "close": r.close}
                        for r in bm_data
                    ]).set_index("date")
                    df_bm.sort_index(inplace=True)
                    # Align index to strategy equity curve
                    df_bm = df_bm.reindex(df_res.index, method="ffill")
                    bm_start = df_bm["close"].dropna().iloc[0] if not df_bm["close"].dropna().empty else None
                    if bm_start:
                        bm_series = (df_bm["close"] / bm_start) * self.initial_capital
                        # Overwrite benchmark_equity in equity_curve
                        bm_dict = bm_series.to_dict()
                        equity_curve = [
                            EquityPoint(
                                date=pt.date,
                                equity=pt.equity,
                                benchmark_equity=bm_dict.get(
                                    pd.to_datetime(pt.date).date()
                                ),
                            )
                            for pt in equity_curve
                        ]
                        benchmark_label = BENCHMARK_LABELS.get(
                            benchmark_ticker, benchmark_ticker
                        )
            except Exception as exc:
                logger.warning("Benchmark fetch failed for %s: %s", benchmark_ticker, exc)

        # ── Sprint 25: trade log extraction ──────────────────────────────────
        trade_log: list[TradeRecord] = []
        if "position" in df_res.columns and "close" in df_res.columns:
            pos      = df_res["position"]
            closes   = df_res["close"]
            idx_list = df_res.index.tolist()

            entry_idx:   int | None   = None
            entry_price: float | None = None

            # Use 0.05 threshold to handle fractional positions (macro_responsive)
            # without generating spurious micro-trades on every sizing adjustment
            ENTRY_THRESHOLD = 0.05

            for i, (date_key, pos_val) in enumerate(pos.items()):
                was_flat   = (entry_idx is None)
                is_long    = float(pos_val) >= ENTRY_THRESHOLD

                if was_flat and is_long:
                    # Entered a new trade
                    entry_idx   = i
                    entry_price = float(closes.iloc[i])

                elif not was_flat and not is_long:
                    # Exited the trade
                    exit_price   = float(closes.iloc[i])
                    holding_days = i - entry_idx  # type: ignore[operator]
                    ret_pct      = (
                        (exit_price - entry_price) / entry_price * 100  # type: ignore[operator]
                        if entry_price else 0.0
                    )
                    trade_log.append(
                        TradeRecord(
                            entry_date   = str(idx_list[entry_idx]),  # type: ignore[index]
                            exit_date    = str(date_key),
                            entry_price  = round(entry_price, 4),      # type: ignore[arg-type]
                            exit_price   = round(exit_price, 4),
                            return_pct   = round(ret_pct, 4),
                            holding_days = max(holding_days, 1),
                        )
                    )
                    entry_idx   = None
                    entry_price = None

        overfitting_warning = stats.sharpe_ratio > 1.2

        return BacktestResponse(
            request=self.request,
            stats=stats,
            equity_curve=equity_curve,
            trade_log=trade_log,
            benchmark_label=benchmark_label,
            assumptions_applied=(
                f"Started with ${self.initial_capital:,.2f}. "
                f"Assumed {self.slippage * 100:.1f}% slippage per trade."
            ),
            overfitting_warning=overfitting_warning,
        )

    # ── Strategy 1: Momentum (SMA Crossover + RSI filter) ────────────────────

    def _run_momentum_strategy(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        SMA crossover with RSI filter.
        Enter long when fast SMA > slow SMA AND RSI > threshold.
        Exit when either condition fails.
        """
        sma_fast_len = int(self.params.get("sma_fast", 50))
        sma_slow_len = int(self.params.get("sma_slow", 200))
        rsi_len      = int(self.params.get("rsi_period", 14))
        rsi_thresh   = float(self.params.get("rsi_threshold", 40))

        df["sma_fast"] = df["close"].rolling(window=sma_fast_len).mean()
        df["sma_slow"] = df["close"].rolling(window=sma_slow_len).mean()

        delta = df["close"].diff()
        gain  = (delta.where(delta > 0, 0)).rolling(window=rsi_len).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(window=rsi_len).mean()
        rs    = gain / loss.replace(0, np.nan)
        df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)

        df["signal"]   = 0
        condition      = (df["sma_fast"] > df["sma_slow"]) & (df["rsi"] > rsi_thresh)
        df.loc[condition, "signal"] = 1
        df["position"] = df["signal"].shift(1).fillna(0)

        return self._apply_position_to_equity(df)

    # ── Strategy 2: Mean Reversion (Bollinger Band + RSI) ────────────────────

    def _run_mean_reversion_strategy(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Bollinger Band mean reversion — buy when price touches lower band AND
        RSI is oversold. Sell when price returns to middle band OR RSI reaches
        the upper threshold.

        Philosophy: counter-trend. Works best in range-bound, low-volatility
        regimes. Use in conjunction with the GAS Regime indicator to determine
        whether this or Momentum is more appropriate.

        Parameters:
          bb_period  (int,   default 20): Bollinger Band lookback
          bb_std     (float, default 2.0): Number of standard deviations for bands
          rsi_period (int,   default 14): RSI lookback
          rsi_low    (float, default 30): Oversold threshold — triggers entry
          rsi_high   (float, default 65): Exit trigger — take profit when RSI reaches here
          hold_days  (int,   default 5):  Max holding period in calendar days
        """
        bb_period  = int(self.params.get("bb_period", 20))
        bb_std     = float(self.params.get("bb_std", 2.0))
        rsi_period = int(self.params.get("rsi_period", 14))
        rsi_low    = float(self.params.get("rsi_low", 30))
        rsi_high   = float(self.params.get("rsi_high", 65))
        hold_days  = int(self.params.get("hold_days", 5))

        # ── Bollinger Bands ───────────────────────────────────────────────────
        df["bb_mid"]   = df["close"].rolling(window=bb_period).mean()
        bb_std_rolling = df["close"].rolling(window=bb_period).std()
        df["bb_upper"] = df["bb_mid"] + bb_std * bb_std_rolling
        df["bb_lower"] = df["bb_mid"] - bb_std * bb_std_rolling
        # %B: where price sits in the band (0 = lower, 1 = upper)
        df["bb_pb"] = (df["close"] - df["bb_lower"]) / (
            df["bb_upper"] - df["bb_lower"]
        ).replace(0, np.nan)

        # ── RSI ───────────────────────────────────────────────────────────────
        delta = df["close"].diff()
        gain  = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss  = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs    = gain / loss.replace(0, np.nan)
        df["rsi"] = (100 - (100 / (1 + rs))).fillna(50)

        # ── Signal generation ─────────────────────────────────────────────────
        # Entry: close touches or crosses below lower band AND RSI oversold
        entry_condition = (df["close"] <= df["bb_lower"]) & (df["rsi"] <= rsi_low)
        # Exit: price returns to mid band OR RSI overbought
        exit_condition  = (df["close"] >= df["bb_mid"])   | (df["rsi"] >= rsi_high)

        # Walk forward to enforce hold_days and avoid consecutive entries
        signals = pd.Series(0, index=df.index)
        in_trade       = False
        days_in_trade  = 0

        for i in range(len(df)):
            if in_trade:
                days_in_trade += 1
                if exit_condition.iloc[i] or days_in_trade >= hold_days:
                    in_trade      = False
                    days_in_trade = 0
                    signals.iloc[i] = 0
                else:
                    signals.iloc[i] = 1
            else:
                if entry_condition.iloc[i]:
                    in_trade        = True
                    days_in_trade   = 1
                    signals.iloc[i] = 1

        df["signal"]   = signals
        df["position"] = df["signal"].shift(1).fillna(0)

        return self._apply_position_to_equity(df)

    # ── Strategy 3: Macro-Responsive ─────────────────────────────────────────

    def _run_macro_responsive_strategy(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Macro-responsive strategy — a simplified proxy that weights position
        size by a momentum score that mimics a "risk-on / risk-off" regime
        indicator. The full GAS macro score isn't available in backtesting
        (that would be lookahead bias), so this uses a VIX-proxy approximation:
        the inverse of the 20-day realised volatility.

        When volatility is low → more aggressive positioning (up to 100%).
        When volatility is high → reduced positioning (scales down to 0%).

        This approximates "buy more when macro is supportive, hold less in
        stressed regimes" without using any forward-looking data.

        Parameters:
          vol_period   (int,   default 20):  Lookback for realised vol
          vol_target   (float, default 0.15): Annual vol target (15%)
          sma_trend    (int,   default 50):   Only buy when price > this SMA
          gas_proxy_threshold (float, default 0.8): Min GAS-proxy score to enter
        """
        vol_period    = int(self.params.get("vol_period", 20))
        vol_target    = float(self.params.get("vol_target", 0.15))
        sma_trend_len = int(self.params.get("sma_trend", 50))

        # ── Daily returns and 20-day realised vol ────────────────────────────
        df["ret"]    = df["close"].pct_change()
        df["rvol"]   = df["ret"].rolling(window=vol_period).std() * np.sqrt(252)
        df["rvol"]   = df["rvol"].bfill().clip(lower=0.01)

        # ── Trend filter: only trade in uptrends ─────────────────────────────
        df["sma_trend"] = df["close"].rolling(window=sma_trend_len).mean()
        in_uptrend      = df["close"] > df["sma_trend"]

        # ── Volatility-targeted position sizing ──────────────────────────────
        # When rvol = vol_target → 100% position. Scale proportionally.
        # Cap at 100%, floor at 0%.
        df["vol_position"] = (vol_target / df["rvol"]).clip(0, 1.0)

        # Only take a position in uptrend
        df["position"] = df["vol_position"].where(in_uptrend, 0.0)
        df["position"] = df["position"].shift(1).fillna(0.0)

        # ── Fractional position returns ───────────────────────────────────────
        df["asset_return"] = df["ret"].fillna(0)
        df["strat_return_gross"] = df["asset_return"] * df["position"]

        df["trade"] = df["position"].diff().abs()
        df["cost"]  = df["trade"] * self.slippage

        df["strat_return_net"] = (df["strat_return_gross"] - df["cost"]).fillna(0)

        df["cum_return"]    = (1 + df["strat_return_net"]).cumprod()
        df["equity"]        = self.initial_capital * df["cum_return"]
        df["bh_cum_return"] = (1 + df["asset_return"]).cumprod()
        df["benchmark_equity"] = self.initial_capital * df["bh_cum_return"]

        stats = self._calculate_performance_metrics(df)
        return df, stats

    # ── Shared equity application ─────────────────────────────────────────────

    def _apply_position_to_equity(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Apply a binary position column to compute equity curve and stats."""
        df["asset_return"]       = df["close"].pct_change()
        df["strat_return_gross"] = df["asset_return"] * df["position"]
        df["trade"]              = df["position"].diff().abs()
        df["cost"]               = df["trade"] * self.slippage
        df["strat_return_net"]   = (df["strat_return_gross"] - df["cost"]).fillna(0)
        df["cum_return"]         = (1 + df["strat_return_net"]).cumprod()
        df["equity"]             = self.initial_capital * df["cum_return"]
        df["bh_cum_return"]      = (1 + df["asset_return"].fillna(0)).cumprod()
        df["benchmark_equity"]   = self.initial_capital * df["bh_cum_return"]
        return df, self._calculate_performance_metrics(df)

    # ── Performance metrics ───────────────────────────────────────────────────

    def _calculate_performance_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        returns = df["strat_return_net"].dropna()
        equity  = df["equity"]

        if len(returns) == 0:
            return self._empty_stats()

        total_return = (equity.iloc[-1] / self.initial_capital) - 1.0
        days         = (df.index[-1] - df.index[0]).days
        years        = days / 365.25 if days > 0 else 1
        ann_return   = ((1 + total_return) ** (1 / years)) - 1.0 if years > 0 else 0

        roll_max     = equity.cummax()
        drawdown     = equity / roll_max - 1.0
        max_drawdown = drawdown.min()

        daily_vol = returns.std()
        sharpe    = (returns.mean() / daily_vol * np.sqrt(252)) if daily_vol > 0 else 0.0

        downside_vol = returns[returns < 0].std()
        sortino      = (returns.mean() / downside_vol * np.sqrt(252)) if downside_vol > 0 else 0.0

        winning_days      = len(returns[returns > 0])
        total_active_days = len(returns[returns != 0])
        win_rate          = (winning_days / total_active_days) if total_active_days > 0 else 0.0

        gross_profit  = returns[returns > 0].sum()
        gross_loss    = abs(returns[returns < 0].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        total_trades     = int(df["trade"].sum()) if "trade" in df.columns else 0
        recovery_factor  = abs(total_return / max_drawdown) if max_drawdown < 0 else 0.0

        return {
            "total_return_pct":      float(total_return * 100),
            "annualized_return_pct": float(ann_return * 100),
            "max_drawdown_pct":      float(max_drawdown * 100),
            "sharpe_ratio":          float(sharpe),
            "sortino_ratio":         float(sortino),
            "win_rate_pct":          float(win_rate * 100),
            "profit_factor":         float(profit_factor),
            "total_trades":          total_trades,
            "recovery_factor":       float(recovery_factor),
            "annualized_volatility_pct": float(daily_vol * np.sqrt(252) * 100) if daily_vol > 0 else 0.0,
            "annualized_mean_pct":       float(returns.mean() * 252 * 100) if daily_vol > 0 else 0.0,
        }

    def _empty_stats(self) -> Dict[str, Any]:
        return {
            "total_return_pct":      0.0,
            "annualized_return_pct": 0.0,
            "max_drawdown_pct":      0.0,
            "sharpe_ratio":          0.0,
            "sortino_ratio":         0.0,
            "win_rate_pct":          0.0,
            "profit_factor":         0.0,
            "total_trades":          0,
            "recovery_factor":       0.0,
            "annualized_volatility_pct": 0.0,
            "annualized_mean_pct":       0.0,
        }

    def run_on_slice(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Run the configured strategy on an already-filtered DataFrame slice."""
        if len(df) < 30:
            return df, self._empty_stats()
        if self.strategy == "momentum":
            return self._run_momentum_strategy(df.copy())
        elif self.strategy == "mean_reversion":
            return self._run_mean_reversion_strategy(df.copy())
        elif self.strategy == "macro_responsive":
            return self._run_macro_responsive_strategy(df.copy())
        return df, self._empty_stats()


# ── Walk-Forward Validation Engine ───────────────────────────────────────────

class WalkForwardEngine:
    """
    Splits the full price history into N overlapping anchor windows, each with a
    training (in-sample) period and a following test (out-of-sample) period.

    Window construction (anchored / expanding-window variant):
      - The full series is divided into (n_splits + 1) equal chunks.
      - Fold k uses chunks 0..k as IS and chunk k+1 as OOS.
      - This mirrors the scikit-learn TimeSeriesSplit with expanding IS window.

    Example (5 splits, full data = 1000 days):
      Fold 1: IS = days 1-166,  OOS = days 167-333
      Fold 2: IS = days 1-333,  OOS = days 334-500
      Fold 3: IS = days 1-500,  OOS = days 501-666
      Fold 4: IS = days 1-666,  OOS = days 667-833
      Fold 5: IS = days 1-833,  OOS = days 834-1000
    """

    def __init__(self, request: WalkForwardRequest):
        self.request = request

    def run(self) -> WalkForwardResponse:
        req = self.request

        # ── Fetch full history ─────────────────────────────────────────────────
        historical_data = OHLCVFetcher.fetch_historical_data(
            req.symbol, period="10y", interval="1d"
        )
        if not historical_data:
            raise ValueError(f"Could not fetch data for {req.symbol}")

        df_full = pd.DataFrame([
            {"date": row.timestamp.date(), "open": row.open, "high": row.high,
             "low": row.low, "close": row.close, "volume": row.volume}
            for row in historical_data
        ]).set_index("date")
        df_full.sort_index(inplace=True)

        n = len(df_full)
        n_splits = req.n_splits

        # Each fold OOS chunk is n / (n_splits + 1) rows
        chunk_size = n // (n_splits + 1)
        if chunk_size < 60:
            raise ValueError(
                f"Not enough data for {n_splits} splits on {req.symbol}. "
                "Try fewer splits or a longer history."
            )

        # ── Build fold specs (anchored/expanding) ──────────────────────────────
        folds: list[WalkForwardFold] = []
        combined_oos_equity_points: list[EquityPoint] = []
        oos_sharpes: list[float] = []
        is_sharpes: list[float] = []
        oos_returns: list[float] = []
        oos_win_rates: list[float] = []
        oos_drawdowns: list[float] = []
        running_capital = req.initial_capital

        for fold_num in range(1, n_splits + 1):
            # IS: rows 0 .. (fold_num * chunk_size) - 1
            is_end_idx  = fold_num * chunk_size
            oos_end_idx = is_end_idx + chunk_size

            df_is  = df_full.iloc[:is_end_idx]
            df_oos = df_full.iloc[is_end_idx:oos_end_idx]

            if len(df_is) < 50 or len(df_oos) < 20:
                continue

            # Build a BacktestRequest-like proxy object
            _br_is = BacktestRequest(
                symbol=req.symbol,
                strategy=req.strategy,
                parameters=req.parameters,
                initial_capital=req.initial_capital,
                slippage_pct=req.slippage_pct,
            )
            _br_oos = BacktestRequest(
                symbol=req.symbol,
                strategy=req.strategy,
                parameters=req.parameters,
                initial_capital=running_capital,  # compound OOS capital
                slippage_pct=req.slippage_pct,
            )

            engine_is  = BacktestingEngine(_br_is)
            engine_oos = BacktestingEngine(_br_oos)

            df_is_res,  is_stats_dict  = engine_is.run_on_slice(df_is)
            df_oos_res, oos_stats_dict = engine_oos.run_on_slice(df_oos)

            is_stats  = BacktestStats(**is_stats_dict)
            oos_stats = BacktestStats(**oos_stats_dict)

            # Build equity point lists (defined outside loop to avoid closure rebind)
            def _equity_points(df_r: pd.DataFrame) -> list[EquityPoint]:
                pts = []
                for idx, row in df_r.iterrows():
                    if "equity" not in df_r.columns or not pd.notna(row.get("equity")):
                        continue
                    pts.append(EquityPoint(
                        date=str(idx),
                        equity=float(row["equity"]),
                        benchmark_equity=(
                            float(row["benchmark_equity"])
                            if "benchmark_equity" in df_r.columns and pd.notna(row.get("benchmark_equity"))
                            else None
                        ),
                    ))
                return pts

            is_equity_pts  = _equity_points(df_is_res)
            oos_equity_pts = _equity_points(df_oos_res)

            # Update compounded OOS capital for next fold
            if oos_equity_pts:
                running_capital = oos_equity_pts[-1].equity
            combined_oos_equity_points.extend(oos_equity_pts)

            oos_sharpes.append(oos_stats.sharpe_ratio)
            is_sharpes.append(is_stats.sharpe_ratio)
            oos_returns.append(oos_stats.total_return_pct)
            oos_win_rates.append(oos_stats.win_rate_pct)
            oos_drawdowns.append(oos_stats.max_drawdown_pct)

            folds.append(WalkForwardFold(
                fold=fold_num,
                train_start=str(df_is.index[0]),
                train_end=str(df_is.index[-1]),
                test_start=str(df_oos.index[0]),
                test_end=str(df_oos.index[-1]),
                in_sample_stats=is_stats,
                in_sample_equity=is_equity_pts,
                out_of_sample_stats=oos_stats,
                out_of_sample_equity=oos_equity_pts,
            ))

        if not folds:
            raise ValueError("Walk-forward produced no valid folds. Check data availability.")

        # ── Aggregate OOS metrics ──────────────────────────────────────────────
        avg_is_sharpe  = float(np.mean(is_sharpes))  if is_sharpes  else 0.0
        avg_oos_sharpe = float(np.mean(oos_sharpes)) if oos_sharpes else 0.0
        degradation    = float(avg_is_sharpe - avg_oos_sharpe)

        # OOS total return = compound all OOS fold returns
        oos_total_return = float(
            np.prod([1 + r / 100 for r in oos_returns]) - 1
        ) * 100 if oos_returns else 0.0

        worst_oos_dd = float(min(oos_drawdowns)) if oos_drawdowns else 0.0

        overfitting_warning = degradation > 0.4 or avg_oos_sharpe < 0.3

        return WalkForwardResponse(
            request=req,
            folds=folds,
            oos_total_return_pct=oos_total_return,
            oos_avg_sharpe=avg_oos_sharpe,
            oos_avg_win_rate=float(np.mean(oos_win_rates)) if oos_win_rates else 0.0,
            oos_max_drawdown_pct=worst_oos_dd,
            avg_sharpe_degradation=degradation,
            combined_oos_equity=combined_oos_equity_points,
            overfitting_warning=overfitting_warning,
        )
