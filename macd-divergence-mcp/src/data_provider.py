"""Pluggable OHLC data sources.

Every provider returns a DataFrame indexed by datetime with columns:
open, high, low, close, volume (all float64 except volume which is int64-ish).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import pandas as pd

STANDARD_COLUMNS = ["open", "high", "low", "close", "volume"]


class DataProvider(ABC):
    @abstractmethod
    def get_ohlc(self, ticker: str, interval: str = "1d", lookback: str = "6mo") -> pd.DataFrame:
        """Return OHLCV data for a ticker.

        interval: bar size, e.g. "1h", "4h", "1d"
        lookback: how far back to fetch, provider-specific string (e.g. yfinance period)
        """
        raise NotImplementedError


class YFinanceProvider(DataProvider):
    """Data source backed by the yfinance package. No API key required."""

    def get_ohlc(self, ticker: str, interval: str = "1d", lookback: str = "6mo") -> pd.DataFrame:
        import yfinance as yf

        df = yf.download(
            ticker,
            period=lookback,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty:
            raise ValueError(f"No OHLC data returned for {ticker!r} (interval={interval}, lookback={lookback})")

        # yfinance returns a MultiIndex column set when given certain params; flatten it.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.rename(columns=str.lower)
        missing = [c for c in STANDARD_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(f"YFinanceProvider response for {ticker!r} is missing columns: {missing}")

        df = df[STANDARD_COLUMNS].copy()
        df.index.name = "date"
        return df


class EToroProvider(DataProvider):
    """Stub for an eToro-backed data source.

    Not implemented yet — pending confirmation that the eToro MCP connector
    exposes historical OHLC candle data at usable resolutions (1H/4H).
    Calling get_ohlc() raises NotImplementedError until that's wired up.
    """

    def get_ohlc(self, ticker: str, interval: str = "1d", lookback: str = "6mo") -> pd.DataFrame:
        raise NotImplementedError(
            "EToroProvider.get_ohlc() is not implemented. "
            "See macd-divergence-mcp step 4 in project setup."
        )


def get_data_provider(name: str | None = None) -> DataProvider:
    """Factory. Reads DATA_PROVIDER env var ('yfinance' | 'etoro') if name not given."""
    name = (name or os.environ.get("DATA_PROVIDER", "yfinance")).strip().lower()
    if name == "yfinance":
        return YFinanceProvider()
    if name == "etoro":
        return EToroProvider()
    raise ValueError(f"Unknown DATA_PROVIDER: {name!r} (expected 'yfinance' or 'etoro')")
