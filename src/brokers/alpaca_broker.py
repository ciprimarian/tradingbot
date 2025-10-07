#src/brokers/alpaca_broker.py

import requests
from requests.auth import settings

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
