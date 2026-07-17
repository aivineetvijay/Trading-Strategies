"""Orchestrates per-ticker and watchlist analysis: pulls OHLC from a
DataProvider, runs the indicators, and combines them into a signal."""

from __future__ import annotations

from .data_provider import DataProvider, get_data_provider
from .indicators import (
    compute_macd,
    detect_bullish_divergence,
    detect_histogram_breakout,
    get_support_resistance,
)


class MACDDivergenceStrategy:
    def __init__(
        self,
        data_provider: DataProvider | None = None,
        sr_order: int = 5,
        sr_tolerance_pct: float = 0.5,
        sr_min_touches: int = 2,
        div_order: int = 5,
        div_min_gap: int = 5,
        div_max_gap: int = 60,
        hist_lookback_bars: int = 3,
        near_support_pct: float = 1.5,
        signal_lookback_bars: int = 5,
    ):
        self.provider = data_provider or get_data_provider()
        self.sr_order = sr_order
        self.sr_tolerance_pct = sr_tolerance_pct
        self.sr_min_touches = sr_min_touches
        self.div_order = div_order
        self.div_min_gap = div_min_gap
        self.div_max_gap = div_max_gap
        self.hist_lookback_bars = hist_lookback_bars
        self.near_support_pct = near_support_pct
        self.signal_lookback_bars = signal_lookback_bars

    def analyze_ticker(self, ticker: str, interval: str = "1d", lookback: str = "6mo") -> dict:
        df = self.provider.get_ohlc(ticker, interval=interval, lookback=lookback)
        macd_df = compute_macd(df["close"])

        levels = get_support_resistance(
            df, order=self.sr_order, tolerance_pct=self.sr_tolerance_pct, min_touches=self.sr_min_touches
        )
        divergences = detect_bullish_divergence(
            df, macd_df, order=self.div_order, min_gap=self.div_min_gap, max_gap=self.div_max_gap
        )
        breakouts = detect_histogram_breakout(macd_df, lookback_bars=self.hist_lookback_bars)

        current_price = float(df["close"].iloc[-1])
        n_bars = len(df)

        supports_below = [l for l in levels if l["level"] <= current_price]
        nearest_support = max(supports_below, key=lambda l: l["level"]) if supports_below else None
        near_support = False
        if nearest_support:
            near_support = abs(current_price - nearest_support["level"]) / current_price * 100 <= self.near_support_pct

        # "recent" = within signal_lookback_bars of the end of the series
        recent_divergence = divergences[-1] if divergences else None
        divergence_is_recent = False
        if recent_divergence:
            second_low_date = recent_divergence["second_low"]["date"]
            pos = df.index.astype(str).str.startswith(second_low_date)
            if pos.any():
                idx = int(pos.to_numpy().nonzero()[0][-1])
                divergence_is_recent = (n_bars - 1 - idx) < self.signal_lookback_bars

        recent_breakout = None
        for b in breakouts:
            if b["bars_from_end"] < self.hist_lookback_bars:
                recent_breakout = b
                break

        signal = bool(divergence_is_recent and near_support)

        summary_bits = []
        if divergence_is_recent:
            summary_bits.append("recent bullish MACD divergence")
        if near_support and nearest_support:
            summary_bits.append(f"price near support at {nearest_support['level']}")
        if recent_breakout:
            summary_bits.append("MACD histogram just turned positive")
        summary = "; ".join(summary_bits) if summary_bits else "no active setup"

        return {
            "ticker": ticker,
            "interval": interval,
            "lookback": lookback,
            "as_of": str(df.index[-1]),
            "current_price": round(current_price, 2),
            "support_resistance": levels,
            "nearest_support": nearest_support,
            "near_support": near_support,
            "divergences": divergences,
            "histogram_breakouts": breakouts,
            "recent_breakout": recent_breakout,
            "signal": signal,
            "summary": summary,
        }

    def scan_watchlist(self, tickers: list[str], interval: str = "1d", lookback: str = "6mo") -> dict:
        results = {}
        signals = []
        for ticker in tickers:
            try:
                result = self.analyze_ticker(ticker, interval=interval, lookback=lookback)
                results[ticker] = result
                if result["signal"]:
                    signals.append(ticker)
            except Exception as exc:  # noqa: BLE001 - surface per-ticker errors without failing the whole scan
                results[ticker] = {"error": str(exc)}
        return {"signals": signals, "results": results}
