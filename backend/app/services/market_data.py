import yfinance as yf
import pandas as pd
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.schemas.data_models import OHLCVData, MacroData

logger = logging.getLogger(__name__)


# ── Intraday lookback limits enforced by yfinance ─────────────────────────────
# yfinance silently returns empty data if you exceed these limits.
# These are the maximums — stay within them.
#
#   1h  → max 730 days (but in practice fetching 730d at once is slow/unreliable)
#   4h  → NOT a native yfinance interval; must resample from 1h
#   1d  → unlimited (years of history available)
#   1wk → unlimited
#   1mo → unlimited
#
# For intraday (1h) we fetch in 60-day chunks and concatenate to get up to 730 days.
# This is the correct approach — fetching "730d" as a single request often returns
# only the most recent ~60 days due to a known yfinance silent truncation issue.

INTRADAY_CHUNK_DAYS = 60        # max per single yfinance intraday request
INTRADAY_MAX_DAYS   = 730       # hard cap on 1h data availability


class OHLCVFetcher:
    """Service to fetch historical OHLCV data from Yahoo Finance.
    
    KEY FIX: intraday (1h) data must be fetched in chunks because yfinance
    silently truncates requests longer than ~60 days. This was the primary
    cause of models training on too few bars and producing unreliable results.
    """

    @staticmethod
    def fetch_historical_data(
        symbol: str,
        period: str = "1y",
        interval: str = "1d",
    ) -> List[OHLCVData]:
        """
        Fetch historical OHLCV data for a given symbol.

        For intraday intervals (1h, 4h), uses chunked fetching to work around
        the yfinance 60-day silent truncation limit. Assembles up to 730 days
        of 1h data, or 730 days of 4h data (resampled from 1h).

        For daily/weekly/monthly intervals, fetches in a single request.

        Args:
            symbol:   Ticker symbol (e.g. 'AAPL')
            period:   Used only for daily+ intervals. For intraday, we always
                      fetch as many days as possible (up to 730). Pass '730d'
                      to signal max intraday fetch.
            interval: '1h', '4h', '1d', '1wk', '1mo'

        Returns:
            List[OHLCVData] sorted ascending by timestamp.
        """
        logger.info(f"Fetching {interval} data for {symbol} (period={period})")

        if interval in ("1h", "4h"):
            return OHLCVFetcher._fetch_intraday(symbol, interval)
        else:
            return OHLCVFetcher._fetch_daily_or_higher(symbol, period, interval)

    # ── Intraday: chunked fetch ────────────────────────────────────────────────

    @staticmethod
    def _fetch_intraday(symbol: str, interval: str) -> List[OHLCVData]:
        """
        Fetch up to 730 days of 1h bars in 60-day chunks, then resample to
        4h if requested. Concatenates all chunks and deduplicates by timestamp.
        """
        fetch_interval = "1h"  # always fetch 1h; resample to 4h if needed
        end_dt   = datetime.utcnow()
        chunks   = []
        days_fetched = 0

        while days_fetched < INTRADAY_MAX_DAYS:
            chunk_start = end_dt - timedelta(days=INTRADAY_CHUNK_DAYS)
            logger.debug(
                f"Fetching chunk for {symbol}: "
                f"{chunk_start.date()} → {end_dt.date()}"
            )

            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(
                    start=chunk_start.strftime("%Y-%m-%d"),
                    end=end_dt.strftime("%Y-%m-%d"),
                    interval=fetch_interval,
                    auto_adjust=True,
                    actions=False,
                )
            except Exception as e:
                logger.warning(f"Chunk fetch failed for {symbol}: {e}")
                break

            if df.empty:
                logger.debug(f"Empty chunk for {symbol} at {chunk_start.date()}, stopping.")
                break

            chunks.append(df)
            days_fetched += INTRADAY_CHUNK_DAYS
            end_dt = chunk_start - timedelta(hours=1)  # step back past this chunk

        if not chunks:
            logger.warning(f"No intraday data fetched for {symbol}")
            return []

        # Combine all chunks, deduplicate, sort ascending
        combined = pd.concat(chunks)
        combined = combined[~combined.index.duplicated(keep="last")]
        combined.sort_index(inplace=True)

        logger.info(
            f"Fetched {len(combined)} total 1h bars for {symbol} "
            f"across {len(chunks)} chunk(s)"
        )

        # Resample 1h → 4h if needed
        if interval == "4h":
            combined = combined.resample("4h", label="left", closed="left").agg(
                {"Open": "first", "High": "max", "Low": "min",
                 "Close": "last", "Volume": "sum"}
            ).dropna()
            logger.info(f"Resampled to {len(combined)} 4h bars for {symbol}")

        return OHLCVFetcher._df_to_ohlcv_list(combined, symbol)

    # ── Daily / weekly / monthly: single request ──────────────────────────────

    @staticmethod
    def _fetch_daily_or_higher(
        symbol: str,
        period: str,
        interval: str,
    ) -> List[OHLCVData]:
        """Single-request fetch for daily+ intervals."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(
                period=period,
                interval=interval,
                auto_adjust=True,
                actions=False,
            )

            if hist.empty:
                logger.warning(f"No {interval} data returned for {symbol}")
                return []

            results = OHLCVFetcher._df_to_ohlcv_list(hist, symbol)
            logger.info(
                f"Fetched {len(results)} {interval} bars for {symbol} "
                f"(period={period})"
            )
            return results

        except Exception as e:
            logger.error(f"Failed to fetch {interval} data for {symbol}: {e}")
            return []

    # ── DataFrame → OHLCVData list ────────────────────────────────────────────

    @staticmethod
    def _df_to_ohlcv_list(df: pd.DataFrame, symbol: str) -> List[OHLCVData]:
        results = []
        for index, row in df.iterrows():
            try:
                timestamp = (
                    index.to_pydatetime()
                    if isinstance(index, pd.Timestamp)
                    else index
                )
                data_point = OHLCVData(
                    symbol=symbol,
                    timestamp=timestamp,
                    open=float(row.get("Open", row.get("open", 0))),
                    high=float(row.get("High", row.get("high", 0))),
                    low=float(row.get("Low", row.get("low", 0))),
                    close=float(row.get("Close", row.get("close", 0))),
                    volume=float(row.get("Volume", row.get("volume", 0))),
                )
                results.append(data_point)
            except Exception as e:
                logger.error(f"Error parsing row for {symbol} at {index}: {e}")
                continue
        return results

    # ── VIX ───────────────────────────────────────────────────────────────────

    @staticmethod
    def fetch_vix(period: str = "1mo") -> List[MacroData]:
        """Fetch VIX closing prices as MacroData."""
        logger.info(f"Fetching {period} of VIX data")
        try:
            ticker = yf.Ticker("^VIX")
            hist = ticker.history(period=period, interval="1d")
            if hist.empty:
                logger.warning("No data returned for ^VIX")
                return []

            results = []
            for index, row in hist.iterrows():
                try:
                    date_obj = index.date() if hasattr(index, "date") else index
                    results.append(MacroData(
                        indicator_name="vix",
                        value=float(row["Close"]),
                        date=date_obj,
                    ))
                except Exception as e:
                    logger.error(f"Error parsing VIX row at {index}: {e}")
                    continue

            logger.info(f"Fetched {len(results)} VIX records")
            return results

        except Exception as e:
            logger.error(f"Failed to fetch VIX: {e}")
            return []
