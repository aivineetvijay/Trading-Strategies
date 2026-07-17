"""Tests for the core indicator functions using synthetic, hand-crafted data
so results are deterministic (no network calls)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.indicators import (
    build_divergence_signals,
    compute_macd,
    detect_bullish_divergence,
    detect_trigger_breakout,
    find_trigger_level,
    get_support_resistance,
)


def _make_df(highs, lows, closes, opens=None, freq="1h"):
    n = len(closes)
    index = pd.date_range("2026-01-01", periods=n, freq=freq)
    opens = opens or closes
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [1000] * n,
        },
        index=index,
    )


def test_compute_macd_basic_shape():
    close = pd.Series(np.linspace(100, 120, 50))
    macd_df = compute_macd(close)
    assert list(macd_df.columns) == ["macd", "signal", "histogram"]
    assert len(macd_df) == 50
    # histogram is macd - signal by construction
    assert np.allclose(macd_df["histogram"], macd_df["macd"] - macd_df["signal"])


def test_get_support_resistance_clusters_repeated_touches():
    # Price oscillates between a ~100 support and ~110 resistance three times.
    lows = [100, 105, 100.3, 105, 99.8, 105]
    highs = [102, 110, 102.2, 109.8, 101.5, 110.1]
    closes = [101, 108, 101, 108, 100.5, 109]
    df = _make_df(highs, lows, closes)

    levels = get_support_resistance(df, order=1, tolerance_pct=1.0, min_touches=2)

    assert len(levels) >= 2
    support_levels = [l for l in levels if l["type"] == "support"]
    resistance_levels = [l for l in levels if l["type"] == "resistance"]
    assert any(abs(l["level"] - 100) < 1 for l in support_levels)
    assert any(abs(l["level"] - 110) < 1 for l in resistance_levels)


def _two_trough_lows() -> np.ndarray:
    """Strictly monotonic ramps between an endpoint - trough(idx5) - peak(idx10)
    - trough(idx15) - endpoint, so argrelextrema finds exactly two true swing
    lows (at idx 5 and 15) with no plateau artifacts."""
    seg1 = np.linspace(30, 10, 6)
    seg2 = np.linspace(10, 30, 6)[1:]
    seg3 = np.linspace(30, 8, 6)[1:]
    seg4 = np.linspace(8, 30, 6)[1:]
    return np.concatenate([seg1, seg2, seg3, seg4])


def test_detect_bullish_divergence_flags_lower_low_higher_macd():
    # Two troughs: price makes a lower low (10 -> 8) while MACD makes a
    # higher low (-2 -> -1), a textbook bullish divergence.
    lows = _two_trough_lows()
    n = len(lows)
    highs = lows + 2
    closes = lows + 1
    df = _make_df(highs, lows, closes)

    macd_vals = np.zeros(n)
    macd_vals[5] = -2.0
    macd_vals[15] = -1.0
    macd_df = pd.DataFrame({"macd": macd_vals, "signal": np.zeros(n), "histogram": np.zeros(n)}, index=df.index)

    divergences = detect_bullish_divergence(df, macd_df, order=3, min_gap=5, max_gap=60)

    assert len(divergences) == 1
    d = divergences[0]
    assert d["first_low"]["price"] == 10
    assert d["second_low"]["price"] == 8
    assert d["first_low"]["macd"] == -2.0
    assert d["second_low"]["macd"] == -1.0
    assert d["bars_apart"] == 10


def test_detect_bullish_divergence_ignores_non_divergent_lows():
    # Price makes a lower low AND MACD makes a lower low too -> no divergence.
    lows = _two_trough_lows()
    n = len(lows)
    highs = lows + 2
    closes = lows + 1
    df = _make_df(highs, lows, closes)

    macd_vals = np.zeros(n)
    macd_vals[5] = -1.0
    macd_vals[15] = -2.0  # lower low on MACD too -> confirms trend, no divergence
    macd_df = pd.DataFrame({"macd": macd_vals, "signal": np.zeros(n), "histogram": np.zeros(n)}, index=df.index)

    divergences = detect_bullish_divergence(df, macd_df, order=3, min_gap=5, max_gap=60)
    assert divergences == []


def test_find_trigger_level_picks_max_histogram_between_troughs():
    n = 10
    hist = [0, 0.1, 0.5, 1.5, 0.8, 0.3, 0, 0, 0, 0]
    idx = pd.date_range("2026-01-01", periods=n, freq="1h")
    macd_df = pd.DataFrame({"macd": hist, "signal": [0] * n, "histogram": hist}, index=idx)

    trigger = find_trigger_level(macd_df, idx1=1, idx2=6)

    assert trigger is not None
    assert trigger["bar_index"] == 3
    assert trigger["level"] == 1.5


def test_find_trigger_level_none_when_troughs_adjacent():
    n = 5
    hist = [0, 1, 2, 3, 4]
    idx = pd.date_range("2026-01-01", periods=n, freq="1h")
    macd_df = pd.DataFrame({"macd": hist, "signal": [0] * n, "histogram": hist}, index=idx)
    assert find_trigger_level(macd_df, idx1=1, idx2=2) is None


def test_detect_trigger_breakout_finds_first_bar_above_level():
    n = 10
    hist = [0, 0, 0, 1.5, 0.8, 0.3, 1.2, 1.6, 2.0, 0.5]
    idx = pd.date_range("2026-01-01", periods=n, freq="1h")
    macd_df = pd.DataFrame({"macd": hist, "signal": [0] * n, "histogram": hist}, index=idx)
    trigger = {"bar_index": 3, "date": "2026-01-01", "level": 1.5}

    breakout = detect_trigger_breakout(macd_df, trigger, after_idx=5)

    assert breakout is not None
    assert breakout["bar_index"] == 7  # first bar after idx 5 where histogram (1.6) > 1.5
    assert breakout["histogram"] == 1.6


def test_detect_trigger_breakout_none_if_never_exceeds():
    n = 8
    hist = [0, 0, 0, 1.5, 0.1, 0.2, 0.3, 0.4]
    idx = pd.date_range("2026-01-01", periods=n, freq="1h")
    macd_df = pd.DataFrame({"macd": hist, "signal": [0] * n, "histogram": hist}, index=idx)
    trigger = {"bar_index": 3, "date": "2026-01-01", "level": 1.5}

    assert detect_trigger_breakout(macd_df, trigger, after_idx=3) is None


def test_build_divergence_signals_end_to_end():
    lows = _two_trough_lows()
    n = len(lows)
    highs = lows + 2
    closes = lows + 1
    df = _make_df(highs, lows, closes)

    hist = np.zeros(n)
    hist[5] = -2.0
    hist[10] = 1.5  # peak between the two troughs -> trigger line
    hist[15] = -1.0
    hist[18] = 2.0  # breaks above the 1.5 trigger line after the second trough
    macd_df = pd.DataFrame({"macd": hist, "signal": np.zeros(n), "histogram": hist}, index=df.index)

    divergences = detect_bullish_divergence(df, macd_df, order=3, min_gap=5, max_gap=60)
    signals = build_divergence_signals(macd_df, divergences)

    assert len(signals) == 1
    sig = signals[0]
    assert sig["trigger_line"]["level"] == 1.5
    assert sig["breakout"] is not None
    assert sig["breakout"]["bar_index"] == 18
    assert sig["triggered"] is True
