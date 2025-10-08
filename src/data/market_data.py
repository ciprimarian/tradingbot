# src/data/market_data.py

import requests
import pandas as pd
from config import settings

class MarketData:
    def __init__(self):
        self.base_url = "https://data.alpaca.markets"
        self.headers = {
            'APCA-API-KEY-ID': settings.ALPACA_API_KEY,
            'APCA-API-SECRET-KEY': settings.ALPACA_SECRET_KEY
        }
        print("market Data handler initialized")

    def get_historical_bars(self, symbol: str, timeframe: str, start: str, limit: int = 100):
        endpoint = f"/v2/stocks/{symbol}/bars"
        parms = {
            "timeframe": timeframe,
            "start": start,
            "limit": limit,
            "adjustment": "raw" #for pure price data
        }
        try:
            print(f"Fetching {limit} bars for {symbol} with timeframe {timeframe} starting from {start}...")
            response = requests.get(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                params=parms,
                timeout=30,
                )
            response.raise_for_status()

            data = response.json()
            bars = data.get('bars', [])
            df = pd.DataFrame(data['bars'])
            if df.empty:
                print(f"No data returned for {symbol}. The symbol might be incored or no data available for the period")
                return None
            
            df['t'] = pd.to_datetime(df['t'])
            df.set_index('t', inplace=True)
            df.rename(columns={'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}, inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            print("Succesfully fetched and processed data")
            return df
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            print("Response Body:", err.response.text)
            return None
        except Exception as e:
            print(f"AN unexpected error occured: {e}")
            return None

