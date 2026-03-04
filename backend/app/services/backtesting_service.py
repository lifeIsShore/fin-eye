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

    SUPPORTED_STRATEGIES = ["momentum"]

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
            raise ValueError(f"Strategy '{self.strategy}' is not supported. Choose from: {self.SUPPORTED_STRATEGIES}")

        # Fetch data. For MVP, we fetch 5y of historical data.
        # Start/End date filtering is done after fetching the raw series.
        historical_data = OHLCVFetcher.fetch_historical_data(self.symbol, period="5y", interval="1d")
        
        if not historical_data:
            raise ValueError(f"Could not fetch data for symbol {self.symbol}")

        # Convert to DataFrame
        df = pd.DataFrame([
            {
                "date": row.timestamp.date(),
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "volume": row.volume
            } for row in historical_data
        ]).set_index("date")
        
        # Sort index just in case
        df.sort_index(inplace=True)

        # Apply date filters if provided
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
            raise ValueError(f"Not enough data points ({len(df)}) for {self.symbol} after filtering to run a reliable backtest.")

        # Run specific strategy
        if self.strategy == "momentum":
            df_res, stats_dict = self._run_momentum_strategy(df)
        else:
            raise ValueError(f"Strategy {self.strategy} is not fully implemented.")

        # Map to Response schemas
        stats = BacktestStats(**stats_dict)
        
        equity_curve = [
            EquityPoint(date=str(idx), equity=row["equity"]) 
            for idx, row in df_res.iterrows() if pd.notna(row["equity"])
        ]

        return BacktestResponse(
            request=self.request,
            stats=stats,
            equity_curve=equity_curve,
            assumptions_applied=f"Started with ${self.initial_capital:,.2f}. Assumed {self.slippage*100}% slippage per trade."
        )

    def _run_momentum_strategy(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Simple Moving Average Crossover with optional RSI filter.
        Params:
            sma_fast (int): default 50
            sma_slow (int): default 200
            rsi_period (int): default 14
            rsi_threshold (float): Only buy if RSI > this (default 0 meant unused, let's say 40)
        """
        sma_fast_len = int(self.params.get("sma_fast", 50))
        sma_slow_len = int(self.params.get("sma_slow", 200))
        rsi_len = int(self.params.get("rsi_period", 14))
        rsi_thresh = float(self.params.get("rsi_threshold", 40))

        # Calculate Indicators
        df["sma_fast"] = df["close"].rolling(window=sma_fast_len).mean()
        df["sma_slow"] = df["close"].rolling(window=sma_slow_len).mean()
        
        # RSI calculation
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_len).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_len).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(50) # Fallback

        # Signal Generation (1 = Long, 0 = Cash)
        # Condition: Fast > Slow AND RSI > Threshold
        df["signal"] = 0
        condition = (df["sma_fast"] > df["sma_slow"]) & (df["rsi"] > rsi_thresh)
        df.loc[condition, "signal"] = 1

        # Shift signal by 1 so we calculate returns based on trade executed at next open (simplification)
        df["position"] = df["signal"].shift(1).fillna(0)

        # Calculate Returns
        # Simple daily return of the asset
        df["asset_return"] = df["close"].pct_change()
        
        # Gross strategy return
        df["strat_return_gross"] = df["asset_return"] * df["position"]

        # Calculate trading costs (Slippage)
        # A trade occurs when position changes
        df["trade"] = df["position"].diff().abs()
        df["cost"] = df["trade"] * self.slippage
        
        # Net strategy return
        df["strat_return_net"] = df["strat_return_gross"] - df["cost"]
        df["strat_return_net"] = df["strat_return_net"].fillna(0)

        # Calculate Equity Curve
        df["cum_return"] = (1 + df["strat_return_net"]).cumprod()
        df["equity"] = self.initial_capital * df["cum_return"]

        stats = self._calculate_performance_metrics(df)
        return df, stats

    def _calculate_performance_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates standard backtest metrics from the net strategy returns."""
        returns = df["strat_return_net"]
        equity = df["equity"]

        # Valid days only
        returns = returns.dropna()
        if len(returns) == 0:
            return self._empty_stats()

        total_return = (equity.iloc[-1] / self.initial_capital) - 1.0

        # Annualized return (assuming 252 trading days)
        days = (df.index[-1] - df.index[0]).days
        years = days / 365.25 if days > 0 else 1
        ann_return = ((1 + total_return) ** (1 / years)) - 1.0 if years > 0 else 0

        # Max Drawdown
        roll_max = equity.cummax()
        drawdown = equity / roll_max - 1.0
        max_drawdown = drawdown.min()

        # Sharpe Ratio (daily risk free rate approx 0)
        daily_vol = returns.std()
        sharpe = (returns.mean() / daily_vol * np.sqrt(252)) if daily_vol > 0 else 0.0

        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std()
        sortino = (returns.mean() / downside_vol * np.sqrt(252)) if downside_vol > 0 else 0.0

        # Win Rate
        winning_days = len(returns[returns > 0])
        total_active_days = len(returns[returns != 0])
        win_rate = (winning_days / total_active_days) if total_active_days > 0 else 0.0

        # Profit Factor
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        # Total Trades
        total_trades = int(df["trade"].sum())

        return {
            "total_return_pct": float(total_return * 100),
            "annualized_return_pct": float(ann_return * 100),
            "max_drawdown_pct": float(max_drawdown * 100),
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "win_rate_pct": float(win_rate * 100),
            "profit_factor": float(profit_factor),
            "total_trades": total_trades
        }

    def _empty_stats(self) -> Dict[str, Any]:
        return {
            "total_return_pct": 0.0,
            "annualized_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0
        }
