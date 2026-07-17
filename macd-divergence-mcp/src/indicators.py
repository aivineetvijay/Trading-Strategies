"""Core technical indicators: MACD, support/resistance clustering,
bullish divergence detection, and MACD histogram breakout detection.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Standard MACD: fast/slow EMA crossover plus signal-line EMA of the MACD line."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "histogram": histogram})


def _dedupe_extrema(idx: np.ndarray, min_spacing: int) -> np.ndarray:
    """argrelextrema can return runs of adjacent indices on flat plateaus; collapse
    any indices closer together than min_spacing down to a single representative."""
    if len(idx) == 0:
        return idx
    out = [idx[0]]
    for i in idx[1:]:
        if i - out[-1] >= min_spacing:
            out.append(i)
    return np.array(out)


def find_swing_points(df: pd.DataFrame, order: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Locate swing highs (in 'high') and swing lows (in 'low') using a rolling
    window comparison. `order` = number of bars on each side that must be
    lower/higher for a point to count as a local extreme. Larger order = fewer,
    more significant swings."""
    highs_idx = argrelextrema(df["high"].values, np.greater_equal, order=order)[0]
    lows_idx = argrelextrema(df["low"].values, np.less_equal, order=order)[0]
    highs_idx = _dedupe_extrema(highs_idx, order)
    lows_idx = _dedupe_extrema(lows_idx, order)
    return highs_idx, lows_idx


def _cluster_levels(points: list[tuple[float, pd.Timestamp, str]], tolerance_pct: float) -> list[dict]:
    """Greedy price clustering: each swing point joins the nearest existing
    cluster if within tolerance_pct of that cluster's running mean, else it
    starts a new cluster."""
    clusters: list[dict] = []
    for price, date, kind in sorted(points, key=lambda p: p[0]):
        placed = False
        for c in clusters:
            if abs(price - c["mean"]) / c["mean"] * 100 <= tolerance_pct:
                c["points"].append((price, date, kind))
                c["mean"] = float(np.mean([p[0] for p in c["points"]]))
                placed = True
                break
        if not placed:
            clusters.append({"mean": price, "points": [(price, date, kind)]})

    levels = []
    for c in clusters:
        kinds = [p[2] for p in c["points"]]
        level_type = "resistance" if kinds.count("high") >= kinds.count("low") else "support"
        last_touch = max(p[1] for p in c["points"])
        levels.append(
            {
                "level": round(c["mean"], 2),
                "type": level_type,
                "touches": len(c["points"]),
                "last_touch": str(pd.Timestamp(last_touch).date()),
            }
        )
    levels.sort(key=lambda l: l["level"])
    return levels


def get_support_resistance(
    df: pd.DataFrame,
    order: int = 5,
    tolerance_pct: float = 0.5,
    min_touches: int = 2,
) -> list[dict]:
    """Cluster swing highs/lows into horizontal S/R levels.

    order: swing-point sensitivity (passed to find_swing_points)
    tolerance_pct: % price distance within which two swings count as the same level
    min_touches: drop levels touched fewer than this many times (noise filter)
    """
    highs_idx, lows_idx = find_swing_points(df, order=order)
    points = [(float(df["high"].iloc[i]), df.index[i], "high") for i in highs_idx]
    points += [(float(df["low"].iloc[i]), df.index[i], "low") for i in lows_idx]
    levels = _cluster_levels(points, tolerance_pct=tolerance_pct)
    return [l for l in levels if l["touches"] >= min_touches]


def detect_bullish_divergence(
    df: pd.DataFrame,
    macd_df: pd.DataFrame,
    order: int = 5,
    min_gap: int = 5,
    max_gap: int = 60,
) -> list[dict]:
    """Classic bullish divergence: price prints a lower swing low while the
    MACD line prints a higher low over the same two pivots.

    order: swing-low sensitivity (passed to find_swing_points)
    min_gap / max_gap: only compare swing-low pairs this many bars apart
    """
    _, lows_idx = find_swing_points(df, order=order)
    divergences = []
    for i in range(1, len(lows_idx)):
        idx1, idx2 = lows_idx[i - 1], lows_idx[i]
        gap = idx2 - idx1
        if gap < min_gap or gap > max_gap:
            continue
        price1, price2 = float(df["low"].iloc[idx1]), float(df["low"].iloc[idx2])
        macd1, macd2 = float(macd_df["macd"].iloc[idx1]), float(macd_df["macd"].iloc[idx2])
        if price2 < price1 and macd2 > macd1:
            divergences.append(
                {
                    "type": "bullish_divergence",
                    "first_low": {
                        "date": str(pd.Timestamp(df.index[idx1]).date()),
                        "price": round(price1, 2),
                        "macd": round(macd1, 4),
                    },
                    "second_low": {
                        "date": str(pd.Timestamp(df.index[idx2]).date()),
                        "price": round(price2, 2),
                        "macd": round(macd2, 4),
                    },
                    "bars_apart": int(gap),
                }
            )
    return divergences


def detect_histogram_breakout(macd_df: pd.DataFrame, lookback_bars: int = 3) -> list[dict]:
    """Flag bars where the MACD histogram crosses from <= 0 to > 0 (bullish
    momentum shift). Returns all crossings found; caller decides what counts
    as "recent" using lookback_bars against len(df)."""
    hist = macd_df["histogram"]
    breakouts = []
    for i in range(1, len(hist)):
        if hist.iloc[i - 1] <= 0 and hist.iloc[i] > 0:
            breakouts.append(
                {
                    "date": str(pd.Timestamp(macd_df.index[i]).date()),
                    "histogram": round(float(hist.iloc[i]), 4),
                    "bars_from_end": int(len(hist) - 1 - i),
                }
            )
    return breakouts
