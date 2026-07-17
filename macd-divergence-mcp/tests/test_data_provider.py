"""Tests for data-provider helpers that don't require network access."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_provider import AlphaVantageProvider, _parse_lookback_months, resample_ohlc


@pytest.mark.parametrize(
    "lookback,expected",
    [
        ("1mo", 1),
        ("3mo", 3),
        ("30d", 1),
        ("45d", 2),
        ("1y", 12),
    ],
)
def test_parse_lookback_months(lookback, expected):
    assert _parse_lookback_months(lookback) == expected


def test_parse_lookback_months_rejects_bad_format():
    with pytest.raises(ValueError):
        _parse_lookback_months("banana")


def test_resample_ohlc_aggregates_4h_from_1h():
    # origin="start_day" anchors 4H bins to midnight, so a run starting at
    # 09:00 lands in the 08:00-12:00 bin (hours 9,10,11 -> 3 bars), then a
    # full 12:00-16:00 bin (hours 12-15 -> 4 bars), then a partial trailing bin.
    index = pd.date_range("2026-01-01 09:00", periods=8, freq="1h")
    df = pd.DataFrame(
        {
            "open": [1, 2, 3, 4, 5, 6, 7, 8],
            "high": [1, 2, 3, 4, 5, 6, 7, 8],
            "low": [1, 2, 3, 4, 5, 6, 7, 8],
            "close": [1, 2, 3, 4, 5, 6, 7, 8],
            "volume": [10] * 8,
        },
        index=index,
    )

    out = resample_ohlc(df, "4h")

    assert len(out) == 3
    first, second, third = out.iloc[0], out.iloc[1], out.iloc[2]
    # first bin covers hours 9,10,11 (values 1,2,3)
    assert first["open"] == 1 and first["close"] == 3 and first["high"] == 3 and first["low"] == 1
    assert first["volume"] == 30
    # second bin covers hours 12,13,14,15 (values 4,5,6,7)
    assert second["open"] == 4 and second["close"] == 7 and second["volume"] == 40
    # trailing partial bin covers hour 16 (value 8)
    assert third["open"] == 8 and third["close"] == 8


def test_alphavantage_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("ALPHAVANTAGE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key"):
        AlphaVantageProvider()


def test_alphavantage_provider_rejects_unsupported_interval(monkeypatch):
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "dummy")
    provider = AlphaVantageProvider()
    with pytest.raises(ValueError, match="only supports interval"):
        provider.get_ohlc("AAPL", interval="1d", lookback="1mo")
