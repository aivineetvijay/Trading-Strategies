# macd-divergence-mcp

An MCP (Model Context Protocol) server that screens stocks for the
**MACD Divergence + Support/Resistance** strategy, using Alpha Vantage as the
OHLC data source.

## Strategy

1. **Support/Resistance** — identify horizontal support/resistance levels on
   the **4-hour** chart by clustering swing highs/lows.
2. **Bullish divergence** — switch to the **1-hour** chart and look for
   bullish MACD divergence: price prints a lower low while the MACD line
   prints a higher low over the same two swing lows (sellers losing
   momentum).
3. **Trigger line** — mark the highest point of the MACD histogram between
   the two divergence troughs and treat its height as a trigger line.
4. **Buy signal** — once the histogram breaks back above that trigger line
   (and the divergence formed near a 4H support level), fire a buy signal.

Alpha Vantage has no native 4-hour interval, so 4H candles are built by
pulling 60-minute intraday bars and resampling them.

## Setup

```bash
cd macd-divergence-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Get a free API key at https://www.alphavantage.co/support/#api-key, then set
it as an environment variable (see `.env.example`):

```bash
export ALPHAVANTAGE_API_KEY=your_key_here
```

Note: Alpha Vantage's free tier is rate-limited (typically 25 requests/day,
~5/minute). Each ticker analysis makes one intraday API call per calendar
month of history requested (for both the 4H and 1H fetch), so scanning the
full watchlist with a multi-month lookback can exhaust the free quota
quickly — a premium key is recommended for regular use.

## Running the server

```bash
python -m src.server
```

This starts the MCP server over stdio. To use it from Claude Desktop or
Claude Code, add it to your MCP client config, e.g.:

```json
{
  "mcpServers": {
    "macd-divergence": {
      "command": "/absolute/path/to/macd-divergence-mcp/.venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/macd-divergence-mcp",
      "env": {
        "ALPHAVANTAGE_API_KEY": "your_key_here"
      }
    }
  }
}
```

## Tools

- `analyze_ticker(ticker, lookback="2mo")` — full strategy run on one ticker:
  4H support/resistance, 1H divergences, trigger lines, breakout status, and
  the combined buy signal.
- `scan_watchlist(tickers=None, lookback="2mo")` — runs `analyze_ticker`
  across a list of tickers (defaults to the standard watchlist below).
- `scan_default_watchlist(lookback="2mo")` — runs the standard watchlist:
  `AAPL, GOOGL, AVGO, WDC, SNDK, TSLA, MSFT`.
- `get_support_resistance(ticker, lookback="2mo")` — just the 4H
  support/resistance levels (step 1).
- `get_macd_divergence_signals(ticker, lookback="2mo")` — just the 1H
  divergence detections with their trigger lines and breakout status
  (steps 2-4).

`lookback` controls how much intraday history to pull, e.g. `"1mo"`,
`"2mo"`, `"3mo"`.

## Tests

```bash
python -m pytest tests/ -v
```

Tests run entirely on synthetic OHLC/MACD data — no network access or API
key required.

## Project layout

```
src/
  data_provider.py   # AlphaVantageProvider (+ YFinance fallback for local testing)
  indicators.py       # MACD, support/resistance clustering, divergence, trigger-line logic
  strategy.py         # Orchestrates steps 1-4 into per-ticker/watchlist results
  server.py           # FastMCP server exposing the tools above
tests/
  test_indicators.py
  test_data_provider.py
```
