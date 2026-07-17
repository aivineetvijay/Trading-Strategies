"""Pluggable OHLC data sources.

Every provider returns a DataFrame indexed by datetime with columns:
open, high, low, close, volume (all float64 except volume which is int64-ish).
"""

from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

import pandas as pd

STANDARD_COLUMNS = ["open", "high", "low", "close", "volume"]

ALPHAVANTAGE_BASE_URL = "https://www.alphavantage.co/query"


class DataProvider(ABC):
    @abstractmethod
    def get_ohlc(self, ticker: str, interval: str = "1d", lookback: str = "6mo") -> pd.DataFrame:
        """Return OHLCV data for a ticker.

        interval: bar size, e.g. "1h", "4h", "1d"
        lookback: how far back to fetch, provider-specific string (e.g. yfinance period)
        """
        raise NotImplementedError


def _parse_lookback_months(lookback: str) -> int:
    """Parse strings like '2mo', '90d', '1y' into a whole number of calendar
    months to pull from Alpha Vantage's intraday `month` slices. Rounds up."""
    lookback = lookback.strip().lower()
    if lookback.endswith("mo"):
        return max(1, int(lookback[:-2]))
    if lookback.endswith("d"):
        return max(1, -(-int(lookback[:-1]) // 30))  # ceil division
    if lookback.endswith("y"):
        return max(1, int(lookback[:-1]) * 12)
    raise ValueError(f"Unrecognized lookback format: {lookback!r} (expected e.g. '2mo', '90d', '1y')")


class AlphaVantageProvider(DataProvider):
    """Data source backed by the Alpha Vantage REST API.

    Requires an API key, read from the `alphavantage_api_key` constructor arg
    or the ALPHAVANTAGE_API_KEY environment variable.

    Alpha Vantage has no native 4-hour interval, so interval="4h" is built by
    pulling 60min intraday bars and resampling them into 4-hour candles.
    """

    INTRADAY_ALIASES = {"1h": "60min", "60min": "60min", "1hour": "60min"}

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ALPHAVANTAGE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "AlphaVantageProvider requires an API key. Set the ALPHAVANTAGE_API_KEY "
                "environment variable or pass alphavantage_api_key explicitly."
            )

    def _fetch_month(self, ticker: str, month: str) -> pd.DataFrame:
        import requests

        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": ticker,
            "interval": "60min",
            "month": month,
            "outputsize": "full",
            "datatype": "json",
            "apikey": self.api_key,
        }
        resp = requests.get(ALPHAVANTAGE_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        payload = resp.json()

        for error_key in ("Error Message", "Note", "Information"):
            if error_key in payload:
                raise ValueError(f"Alpha Vantage error for {ticker!r} ({month}): {payload[error_key]}")

        series_key = "Time Series (60min)"
        series = payload.get(series_key)
        if not series:
            raise ValueError(f"Alpha Vantage response for {ticker!r} ({month}) missing {series_key!r}: {payload}")

        rows = []
        for ts, bar in series.items():
            rows.append(
                {
                    "date": ts,
                    "open": float(bar["1. open"]),
                    "high": float(bar["2. high"]),
                    "low": float(bar["3. low"]),
                    "close": float(bar["4. close"]),
                    "volume": int(bar["5. volume"]),
                }
            )
        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        return df.set_index("date").sort_index()

    def _fetch_intraday(self, ticker: str, months: int) -> pd.DataFrame:
        today = datetime.now(timezone.utc)
        month_strs = []
        cursor = today
        for _ in range(months):
            month_strs.append(cursor.strftime("%Y-%m"))
            # step back to the previous month
            first_of_month = cursor.replace(day=1)
            cursor = first_of_month - timedelta(days=1)

        frames = []
        for i, month in enumerate(month_strs):
            frames.append(self._fetch_month(ticker, month))
            if i < len(month_strs) - 1:
                time.sleep(1)  # be polite to the API's rate limit

        df = pd.concat(frames)
        df = df[~df.index.duplicated(keep="last")].sort_index()
        return df

    def get_ohlc(self, ticker: str, interval: str = "1h", lookback: str = "2mo") -> pd.DataFrame:
        months = _parse_lookback_months(lookback)
        base_interval = self.INTRADAY_ALIASES.get(interval.lower())

        if base_interval == "60min":
            df = self._fetch_intraday(ticker, months)
        elif interval.lower() == "4h":
            df = self._fetch_intraday(ticker, months)
            df = resample_ohlc(df, "4h")
        else:
            raise ValueError(f"AlphaVantageProvider only supports interval in {{'1h', '4h'}}, got {interval!r}")

        if df.empty:
            raise ValueError(f"No OHLC data returned for {ticker!r} (interval={interval}, lookback={lookback})")
        return df[STANDARD_COLUMNS]


def resample_ohlc(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Resample an OHLCV DataFrame into coarser bars, e.g. 60min bars into '4h' bars."""
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    out = df.resample(rule, origin="start_day").agg(agg).dropna(subset=["open", "high", "low", "close"])
    return out


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
    """Factory. Reads DATA_PROVIDER env var ('alphavantage' | 'yfinance' | 'etoro') if name not given.
    Defaults to 'alphavantage' per the strategy's data source."""
    name = (name or os.environ.get("DATA_PROVIDER", "alphavantage")).strip().lower()
    if name == "alphavantage":
        return AlphaVantageProvider()
    if name == "yfinance":
        return YFinanceProvider()
    if name == "etoro":
        return EToroProvider()
    raise ValueError(f"Unknown DATA_PROVIDER: {name!r} (expected 'alphavantage', 'yfinance', or 'etoro')")
