from __future__ import annotations

from datetime import datetime, timedelta, timezone

import requests

from src.brokers.alpaca_broker import AlpacaBroker
from src.fuzzi.common.models import Bar
from src.fuzzi.config import FuzziSettings


class TapeFeed:
    """Wraps Alpaca data API into Fuzzi Bar format."""

    def __init__(self, settings: FuzziSettings) -> None:
        self.settings = settings
        self.broker = AlpacaBroker()
        self.base_url = "https://data.alpaca.markets"
        self.headers = dict(self.broker.headers)

    def latest_bars(
        self,
        symbols: list[str],
        timeframe: str = "1Day",
        limit: int = 100,
    ) -> dict[str, list[Bar]]:
        symbol_bars: dict[str, list[Bar]] = {}
        start = (datetime.now(timezone.utc) - timedelta(days=max(limit * 3, 10))).isoformat()

        for symbol in symbols:
            endpoint = f"/v2/stocks/{symbol}/bars"
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params={
                    "timeframe": timeframe,
                    "start": start,
                    "limit": limit,
                    "adjustment": "raw",
                },
                timeout=30,
            )
            response.raise_for_status()

            payload = response.json()
            symbol_bars[symbol] = [self._to_bar(symbol, item) for item in payload.get("bars", [])]

        return symbol_bars

    def last_price(self, symbol: str) -> float:
        bars = self.latest_bars([symbol], timeframe=self.settings.runtime.default_timeframe, limit=1)
        latest = bars.get(symbol, [])
        if not latest:
            return 0.0
        return latest[-1].close

    @staticmethod
    def _to_bar(symbol: str, payload: dict[str, object]) -> Bar:
        timestamp = datetime.fromisoformat(str(payload["t"]).replace("Z", "+00:00"))
        return Bar(
            symbol=symbol,
            timestamp=timestamp,
            open=float(payload["o"]),
            high=float(payload["h"]),
            low=float(payload["l"]),
            close=float(payload["c"]),
            volume=float(payload["v"]),
        )

