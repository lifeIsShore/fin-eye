import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Dict, Any, Tuple, Optional

from app.schemas.backtest_models import BacktestRequest, BacktestResponse, BacktestStats, EquityPoint
from app.services.market_data import OHLCVFetcher

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
                pass
        if self.request.end_date:
            try:
                end_dt = datetime.strptime(self.request.end_date, "%Y-%m-%d").date()
                df = df[df.index <= end_dt]
            except ValueError:
                pass

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

        overfitting_warning = stats.sharpe_ratio > 1.2

        return BacktestResponse(
            request=self.request,
            stats=stats,
            equity_curve=equity_curve,
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
        df["rvol"]   = df["rvol"].fillna(method="bfill").clip(lower=0.01)

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
        }
