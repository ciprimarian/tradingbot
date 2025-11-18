#src/brokers/alpaca_broker.py

import requests

from src.utils.common_imports import get_logger
from src.config import settings


class AlpacaBroker:
    """Alpaca broker interface for executing trades and fetching account data"""
    
    def __init__(self):
        self.base_url = settings.BASE_URL
        self.headers = {
            'APCA-API-KEY-ID': settings.ALPACA_API_KEY,
            'APCA-API-SECRET-KEY': settings.ALPACA_SECRET_KEY
        }
        self.logger = get_logger(__name__)
        self.logger.info(f"Alpaca Broker initialized | base_url={self.base_url}")
    
    def get_account_info(self):
        """Fetch account information from Alpaca"""
        try:
            self.logger.debug("Fetching account information...")
            response = requests.get(f"{self.base_url}/v2/account", headers=self.headers)
            response.raise_for_status()
            
            account = response.json()
            self.logger.info(
                f"Account info retrieved | Cash: ${float(account.get('cash', 0)):.2f}, "
                f"Portfolio Value: ${float(account.get('portfolio_value', 0)):.2f}"
            )
            return account
            
        except requests.exceptions.HTTPError as err:
            self.logger.error(f"HTTP Error fetching account info: {err}")
            self.logger.error(f"Response Body: {err.response.text}")
            self.logger.error("Could not connect to Alpaca. Please check your API keys and permissions")
            return None
            
        except Exception as e:
            self.logger.error(f"Unexpected error fetching account info: {e}", exc_info=True)
            return None
    
    def get_market_clock(self):
        """Get market clock information (open status, next open/close times)"""
        try:
            self.logger.debug("Fetching market clock...")
            response = requests.get(f"{self.base_url}/v2/clock", headers=self.headers)
            response.raise_for_status()
            
            clock = response.json()
            is_open = clock.get('is_open', False)
            next_open = clock.get('next_open')
            next_close = clock.get('next_close')
            
            self.logger.debug(
                f"Market clock | is_open={is_open}, next_open={next_open}, next_close={next_close}"
            )
            return clock
            
        except requests.exceptions.HTTPError as err:
            self.logger.error(f"HTTP Error fetching market clock: {err}")
            return None
            
        except Exception as e:
            self.logger.error(f"Unexpected error fetching market clock: {e}", exc_info=True)
            return None
    
    def is_market_open(self):
        """Check if the market is currently open for trading"""
        clock = self.get_market_clock()
        if clock:
            return clock.get('is_open', False)
        return False
        
    def submit_order(self, symbol: str, qty: int, side: str):
        """Submit a market order to Alpaca"""
        endpoint = "/v2/orders"
        order_data = {
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "type": "market",
            "time_in_force": "day"
        }
        
        self.logger.info(f"Submitting {side.upper()} order | Symbol={symbol}, Qty={qty}")
        
        try:
            response = requests.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                json=order_data
            )
            response.raise_for_status()
            
            order_details = response.json()
            order_id = order_details.get('id', 'N/A')
            order_status = order_details.get('status', 'N/A')
            
            self.logger.info(f"Order submitted successfully | Order ID: {order_id}, Status: {order_status}")
            self.logger.debug(f"Order details: {order_details}")
            
            return order_details
            
        except requests.exceptions.HTTPError as err:
            self.logger.error(f"HTTP Error submitting order: {err}")
            self.logger.error(f"Response body: {err.response.text}")
            return None
            
        except Exception as e:
            self.logger.error(f"Unexpected error during order submission: {e}", exc_info=True)
            return None
    
    def get_open_positions(self):
        """Fetch all open positions from Alpaca"""
        endpoint = "/v2/positions"
        
        self.logger.debug("Fetching open positions...")
        
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers)
            response.raise_for_status()
            
            positions = response.json()
            self.logger.info(f"Successfully fetched {len(positions)} open position(s)")
            
            return positions
            
        except requests.exceptions.HTTPError as err:
            self.logger.error(f"HTTP Error fetching positions: {err}")
            self.logger.error(f"Response body: {err.response.text}")
            return None
            
        except Exception as e:
            self.logger.error(f"Unexpected error fetching positions: {e}", exc_info=True)
            return None