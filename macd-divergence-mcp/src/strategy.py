"""Orchestrates the MACD Divergence + Support/Resistance strategy:

  Step 1: identify support/resistance levels on the 4H chart.
  Step 2: on the 1H chart, look for bullish divergence (price lower low,
          MACD higher low).
  Step 3: mark the highest MACD histogram point between the two divergence
          troughs and treat it as a trigger line.
  Step 4: if the histogram later breaks above that trigger line, and the
          divergence formed near a 4H support level, fire the buy signal.
"""

from __future__ import annotations

from .data_provider import DataProvider, get_data_provider, resample_ohlc
from .indicators import (
    build_divergence_signals,
    compute_macd,
    detect_bullish_divergence,
    get_support_resistance,
)

DEFAULT_WATCHLIST = ["AAPL", "GOOGL", "AVGO", "WDC", "SNDK", "TSLA", "MSFT"]


class MACDDivergenceStrategy:
    def __init__(
        self,
        data_provider: DataProvider | None = None,
        higher_interval: str = "4h",
        lower_interval: str = "1h",
        sr_order: int = 5,
        sr_tolerance_pct: float = 0.5,
        sr_min_touches: int = 2,
        div_order: int = 3,
        div_min_gap: int = 5,
        div_max_gap: int = 60,
        near_support_pct: float = 1.5,
        signal_lookback_bars: int = 5,
    ):
        self._provider = data_provider
        self.higher_interval = higher_interval
        self.lower_interval = lower_interval
        self.sr_order = sr_order
        self.sr_tolerance_pct = sr_tolerance_pct
        self.sr_min_touches = sr_min_touches
        self.div_order = div_order
        self.div_min_gap = div_min_gap
        self.div_max_gap = div_max_gap
        self.near_support_pct = near_support_pct
        self.signal_lookback_bars = signal_lookback_bars

    @property
    def provider(self) -> DataProvider:
        # Resolved lazily so constructing a strategy (e.g. at MCP server
        # import time) doesn't require ALPHAVANTAGE_API_KEY to already be set.
        if self._provider is None:
            self._provider = get_data_provider()
        return self._provider

    def analyze_ticker(self, ticker: str, lookback: str = "2mo") -> dict:
        # Fetch the lower (1H) timeframe once; the higher (4H) timeframe is
        # derived from it locally by resampling, so this doesn't cost a
        # second API call (and keeps both timeframes built from the same
        # underlying bars).
        lower_df = self.provider.get_ohlc(ticker, interval=self.lower_interval, lookback=lookback)
        higher_df = resample_ohlc(lower_df, self.higher_interval)

        # Step 1: support/resistance on the higher (4H) timeframe.
        levels = get_support_resistance(
            higher_df, order=self.sr_order, tolerance_pct=self.sr_tolerance_pct, min_touches=self.sr_min_touches
        )

        # Step 2: bullish divergence on the lower (1H) timeframe.
        macd_df = compute_macd(lower_df["close"])
        divergences = detect_bullish_divergence(
            lower_df, macd_df, order=self.div_order, min_gap=self.div_min_gap, max_gap=self.div_max_gap
        )

        # Steps 3 & 4: trigger line between the troughs + histogram breakout.
        divergence_signals = build_divergence_signals(macd_df, divergences)

        current_price = float(lower_df["close"].iloc[-1])
        n_bars = len(lower_df)

        supports_below = [l for l in levels if l["level"] <= current_price]
        nearest_support = max(supports_below, key=lambda l: l["level"]) if supports_below else None

        for sig in divergence_signals:
            second_low_price = sig["divergence"]["second_low"]["price"]
            candidates = [l for l in levels if abs(second_low_price - l["level"]) / second_low_price * 100 <= self.near_support_pct]
            sig["near_support"] = bool(candidates)
            sig["support_level"] = candidates[0] if candidates else None
            sig["is_recent"] = bool(
                sig["breakout"] and sig["breakout"]["bars_from_end"] < self.signal_lookback_bars
            )
            sig["active_signal"] = bool(sig["triggered"] and sig["near_support"] and sig["is_recent"])

        active_signals = [s for s in divergence_signals if s["active_signal"]]
        signal = bool(active_signals)

        summary_bits = []
        if active_signals:
            summary_bits.append(f"{len(active_signals)} confirmed bullish MACD divergence buy signal(s) near support")
        elif any(s["triggered"] for s in divergence_signals):
            summary_bits.append("MACD trigger-line breakout occurred but not near a 4H support level or not recent")
        elif divergence_signals:
            summary_bits.append("bullish divergence detected, awaiting histogram break above trigger line")
        summary = "; ".join(summary_bits) if summary_bits else "no active setup"

        return {
            "ticker": ticker,
            "higher_interval": self.higher_interval,
            "lower_interval": self.lower_interval,
            "lookback": lookback,
            "as_of": str(lower_df.index[-1]),
            "current_price": round(current_price, 2),
            "support_resistance": levels,
            "nearest_support": nearest_support,
            "divergence_signals": divergence_signals,
            "signal": signal,
            "summary": summary,
            "bars_analyzed": n_bars,
        }

    def scan_watchlist(self, tickers: list[str] | None = None, lookback: str = "2mo") -> dict:
        tickers = tickers or DEFAULT_WATCHLIST
        results = {}
        signals = []
        for ticker in tickers:
            try:
                result = self.analyze_ticker(ticker, lookback=lookback)
                results[ticker] = result
                if result["signal"]:
                    signals.append(ticker)
            except Exception as exc:  # noqa: BLE001 - surface per-ticker errors without failing the whole scan
                results[ticker] = {"error": str(exc)}
        return {"signals": signals, "results": results}
