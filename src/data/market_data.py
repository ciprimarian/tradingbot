# src/data/market_data.py
from datetime import datetime
from typing import Optional

import requests
import pandas as pd

from src.config import settings
from src.utils.logger import get_Logger

class MarketData:
    def __init__(self):
        self.base_url = "https://data.alpaca.markets"
        self.headers = {
            'APCA-API-KEY-ID': settings.ALPACA_API_KEY,
            'APCA-API-SECRET-KEY': settings.ALPACA_SECRET_KEY
        }
        self.logger = get_Logger(__name__)
        self.logger.info("Market Data handler initialized | base_url: %s", self.base_url)

    def get_historical_bars(self, symbol: str, timeframe: str, start: str, end: Optional[str] = None, limit: int = 100) -> Optional[pd.DataFrame]:
        endpoint = f"/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": timeframe,
            "start": start,
            "limit": limit,
            "adjustment": "raw" #for pure price data
        }
        if end:
            params["end"] = self._to_iso(end)
        try:
            self.logger.info(f"Fetching bars | symbol=%s, timeframe=%s, start=%s, end=%s, limit=%d", symbol, timeframe, params['start'], params.get("end"), limit)
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=params,
                timeout=30,
                )
            response.raise_for_status()

            data = response.json()
            bars = data.get('bars', [])
            df = pd.DataFrame(data['bars'])
            if not bars:
                self.logger.warning(f"No data returned for %s. The symbol might be incorrect or no data available for the period", symbol)
                return None
            
            df = pd.DataFrame(bars)
            df['t'] = pd.to_datetime(df['t'])
            df.set_index('t', inplace=True)
            df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            print("Succesfully fetched and processed data")
            return df
        except requests.exceptions.HTTPError as err:
            self.logger.error("Response Body: %s", err, err.response.text)
            return None
        except Exception as exc:
            self.logger.exception("An unexpected error occurred fetching bars: %s", exc)
            return None

    @staticmethod
    def _to_iso(value: str) -> str:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return value
        except ValueError:
            dt = datetime.fromisoformat(value)
            return dt.isoformat()