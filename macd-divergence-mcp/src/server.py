"""FastMCP server exposing the MACD Divergence + Support/Resistance
screening strategy as tools, over stdio transport."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .strategy import MACDDivergenceStrategy

mcp = FastMCP("macd-divergence")
strategy = MACDDivergenceStrategy()


@mcp.tool()
def analyze_ticker(ticker: str, interval: str = "1d", lookback: str = "6mo") -> dict:
    """Run full MACD-divergence + support/resistance analysis on a single ticker.

    Returns current price, clustered S/R levels, detected bullish divergences,
    MACD histogram breakouts, and a combined buy signal/summary.
    """
    return strategy.analyze_ticker(ticker, interval=interval, lookback=lookback)


@mcp.tool()
def scan_watchlist(tickers: list[str], interval: str = "1d", lookback: str = "6mo") -> dict:
    """Run analyze_ticker across a list of tickers. Returns which tickers have
    an active signal plus the full per-ticker results."""
    return strategy.scan_watchlist(tickers, interval=interval, lookback=lookback)


@mcp.tool()
def get_support_resistance(ticker: str, interval: str = "1d", lookback: str = "6mo") -> dict:
    """Return only the clustered support/resistance levels for a ticker."""
    result = strategy.analyze_ticker(ticker, interval=interval, lookback=lookback)
    return {
        "ticker": ticker,
        "current_price": result["current_price"],
        "support_resistance": result["support_resistance"],
        "nearest_support": result["nearest_support"],
    }


@mcp.tool()
def get_macd_divergence(ticker: str, interval: str = "1d", lookback: str = "6mo") -> dict:
    """Return only the MACD divergence and histogram-breakout detections for a ticker."""
    result = strategy.analyze_ticker(ticker, interval=interval, lookback=lookback)
    return {
        "ticker": ticker,
        "divergences": result["divergences"],
        "histogram_breakouts": result["histogram_breakouts"],
        "recent_breakout": result["recent_breakout"],
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
