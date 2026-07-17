from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from _common import JSONHandler

from src.strategy import MACDDivergenceStrategy


class handler(JSONHandler):
    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        ticker = (query.get("ticker") or [None])[0]
        lookback = (query.get("lookback") or ["2mo"])[0]

        if not ticker:
            self._send_json({"error": "missing required query param: ticker"}, status=400)
            return

        try:
            strategy = MACDDivergenceStrategy()
            result = strategy.analyze_ticker(ticker.strip().upper(), lookback=lookback, include_series=True)
            self._send_json(result)
        except Exception as exc:  # noqa: BLE001 - surface the error to the client
            self._send_json({"error": str(exc)}, status=500)
