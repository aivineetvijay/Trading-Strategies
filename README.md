# Trading Strategies

This repo has two pieces implementing the **MACD Divergence + Support/Resistance**
strategy (see `macd-divergence-mcp/README.md` for the strategy write-up):

- **`macd-divergence-mcp/`** — a stdio MCP server exposing the strategy as
  tools for an MCP client (Claude Desktop, Claude Code, etc.).
- **Everything else at the repo root** — a Next.js web dashboard that runs
  the same strategy logic (imported directly from `macd-divergence-mcp/src`,
  no reimplementation) and visualizes it: a watchlist screener and a
  per-ticker chart showing support/resistance levels, the bullish divergence,
  its trigger line, and the histogram breakout.

## Web dashboard

```
app/                    Next.js App Router pages (dashboard + ticker detail)
components/              StatusBadge, WatchlistTable, TickerChart (hand-rolled SVG)
lib/                      Shared TypeScript types + signal-status classification
api/                      Vercel Python serverless functions (watchlist, analyze)
  _common.py              Shared JSON/CORS response helper + sys.path wiring
                          into macd-divergence-mcp/src
  requirements.txt        Python deps for the API functions
vercel.json               Bundles macd-divergence-mcp/src into the Python functions
```

`api/watchlist.py` and `api/analyze.py` import `MACDDivergenceStrategy` and
`DEFAULT_WATCHLIST` straight from `macd-divergence-mcp/src/strategy.py` — the
web app and the MCP server share one implementation of the strategy, not two.

### Local development

```bash
npm install
npm run dev
```

The frontend calls `/api/watchlist` and `/api/analyze?ticker=X`. Running the
Python functions locally requires the Vercel CLI (`vercel dev`) — plain
`next dev` alone won't serve `/api/*.py`. Either run `vercel dev`, or point
the frontend's fetch calls at a separately-running instance of the API
during development.

### Required environment variable

Both API functions construct `MACDDivergenceStrategy()`, which needs
`ALPHAVANTAGE_API_KEY` set (get a free key at
https://www.alphavantage.co/support/#api-key). Set it in the Vercel
project's **Settings → Environment Variables** — it's a secret, so it isn't
committed here and can't be set from this repo's code.

### Deploying

This repo is linked to a Vercel project that auto-deploys on push. Pushing
to this branch (or merging to the production branch) builds and deploys the
Next.js frontend plus the two Python API functions automatically, as long as
`ALPHAVANTAGE_API_KEY` is set in the project's environment variables.

Alpha Vantage's free tier is rate-limited (~25 requests/day). Each watchlist
scan makes one API call per ticker (the 4H timeframe is derived locally by
resampling the same 1H fetch, not a second call) — scanning the full
7-ticker default watchlist costs 7 calls per rescan.
