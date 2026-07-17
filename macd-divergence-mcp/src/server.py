"""FastMCP server exposing the MACD Divergence + Support/Resistance
screening strategy as tools, over stdio transport."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .strategy import DEFAULT_WATCHLIST, MACDDivergenceStrategy

mcp = FastMCP("macd-divergence")
strategy = MACDDivergenceStrategy()


@mcp.tool()
def analyze_ticker(ticker: str, lookback: str = "2mo") -> dict:
    """Run the full MACD Divergence + Support/Resistance strategy on a single ticker.

    Step 1: builds support/resistance levels from the 4H chart.
    Step 2: scans the 1H chart for bullish MACD divergence (price lower low, MACD higher low).
    Step 3: marks the highest MACD histogram point between the two divergence troughs as a trigger line.
    Step 4: flags a buy signal once the histogram breaks above that trigger line near a 4H support level.

    lookback controls how much history to pull (e.g. "1mo", "2mo", "3mo").
    Returns current price, 4H support/resistance levels, and each divergence
    with its trigger line, breakout status, and whether it's an active buy signal.
    """
    return strategy.analyze_ticker(ticker, lookback=lookback)


@mcp.tool()
def scan_watchlist(tickers: list[str] | None = None, lookback: str = "2mo") -> dict:
    """Run analyze_ticker across a list of tickers (defaults to the standard
    watchlist: AAPL, GOOGL, AVGO, WDC, SNDK, TSLA, MSFT if omitted).
    Returns which tickers have an active buy signal plus full per-ticker results."""
    return strategy.scan_watchlist(tickers, lookback=lookback)


@mcp.tool()
def scan_default_watchlist(lookback: str = "2mo") -> dict:
    """Run analyze_ticker across the default watchlist (AAPL, GOOGL, AVGO, WDC,
    SNDK, TSLA, MSFT). Returns which tickers have an active buy signal plus
    full per-ticker results."""
    return strategy.scan_watchlist(DEFAULT_WATCHLIST, lookback=lookback)


@mcp.tool()
def get_support_resistance(ticker: str, lookback: str = "2mo") -> dict:
    """Return only the 4H support/resistance levels for a ticker (strategy step 1)."""
    result = strategy.analyze_ticker(ticker, lookback=lookback)
    return {
        "ticker": ticker,
        "current_price": result["current_price"],
        "support_resistance": result["support_resistance"],
        "nearest_support": result["nearest_support"],
    }


@mcp.tool()
def get_macd_divergence_signals(ticker: str, lookback: str = "2mo") -> dict:
    """Return only the 1H bullish MACD divergence detections for a ticker, each
    with its trigger line, histogram breakout status, and active-signal flag
    (strategy steps 2-4)."""
    result = strategy.analyze_ticker(ticker, lookback=lookback)
    return {
        "ticker": ticker,
        "divergence_signals": result["divergence_signals"],
        "signal": result["signal"],
        "summary": result["summary"],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
