from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from _common import JSONHandler

from src.strategy import DEFAULT_WATCHLIST, MACDDivergenceStrategy


class handler(JSONHandler):
    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        lookback = (query.get("lookback") or ["2mo"])[0]
        tickers_param = (query.get("tickers") or [None])[0]
        tickers = (
            [t.strip().upper() for t in tickers_param.split(",") if t.strip()]
            if tickers_param
            else DEFAULT_WATCHLIST
        )

        try:
            strategy = MACDDivergenceStrategy()
            result = strategy.scan_watchlist(tickers, lookback=lookback)
            self._send_json(result)
        except Exception as exc:  # noqa: BLE001 - surface the error to the client
            self._send_json({"error": str(exc)}, status=500)
