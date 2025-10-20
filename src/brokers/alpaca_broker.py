#src/brokers/alpaca_broker.py

import requests
from config import settings
import json

class AlpacaBroker:
    def __init__(self):
        self.base_url = settings.BASE_URL
        self.headers = {
            'APCA-API-KEY-ID': settings.ALPACA_API_KEY,
            'APCA-API-SECRET-KEY': settings.ALPACA_SECRET_KEY
        }
        print("Alpaca Broker initialized with base URL:", self.base_url)
    def get_account_info(self):
        try:
            response = requests.get(f"{self.base_url}/v2/account", headers=self.headers)
            response.raise_for_status() # Raise an error for bad status codes
            return response.json()
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error: {err}")
            print("Response Body:", err.response.text)
            print("\nCould not connect to Alpaca. Please check your API keys and permissions in .env")
            return None
        except Exception as e:
            print(f"AN unexpected error occured: {e}")
            return None
        
    def submit_order(self, symbol: str, qty: int, side: str):
        endpoint = "/v2/orders"
        order_data = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "market",
            "time_in_force": "day"
        }
        print(f"\nSubbmiting {side} order for {qty} shares of {symbol}...")
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=order_data
            )
            response.raise_for_status()
            order_details = response.json()
            print("Order submmited succesfully")
            print("Order details:", order_details)
            return order_details
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error submitting order: {err}")
            print("Response body;", err.response.text)
            return None
        except Exception as e:
            print(f"An unexpected error occured during order submission; {e}")
            return None
    
    def get_open_position(self):
        endpoint = "/v2/positions"
        print("\nFetching open positions:")
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers)
            response.raise_for_status()
            position_data = response.json()
            print("Succesfully fetched positions.")
            return position_data
        except requests.exceptions.HTTPError as err:
            print(f"HTTP Error submitting order: {err}")
            print("Response body;", err.response.text)
            return None
        except Exception as e:
            print(f"An unexpected error occured during order submission; {e}")
            return None