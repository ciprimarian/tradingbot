from src.utils.common_imports import get_logger
from src.brokers.alpaca_broker import AlpacaBroker


class PortfolioManager:
    """Manages portfolio state and positions"""
    
    def __init__(self, broker: AlpacaBroker):
        self.broker = broker
        self.cash = 0.0
        self.portfolio_value = 0.0
        self.positions = {}  # Dictionary to store positions by symbol
        self.logger = get_logger(__name__)
        
        self.logger.info("PortfolioManager initialized")
        self.update_portfolio()  # Initial fetch during creation

    def update_portfolio(self):
        """Update portfolio state from broker"""
        self.logger.debug("Updating portfolio state...")
        
        account_info = self.broker.get_account_info()
        if account_info:
            self.cash = float(account_info.get('cash', 0.0))
            self.portfolio_value = float(account_info.get('portfolio_value', 0.0))
            self.logger.debug(f"Portfolio updated | Cash: ${self.cash:.2f}, Value: ${self.portfolio_value:.2f}")
        else:
            self.logger.warning("Failed to fetch account info during portfolio update")

        open_positions = self.broker.get_open_positions()
        self.positions = {}  # Clear old positions
        
        if open_positions:
            for position in open_positions:
                symbol = position.get('symbol')
                if symbol:
                    self.positions[symbol] = {
                        'qty': int(position.get('qty', 0)),
                        'market_value': float(position.get('market_value', 0.0)),
                        'unrealized_pl': float(position.get('unrealized_pl', 0.0))
                    }
            
            self.logger.info(f"Portfolio update complete | {len(self.positions)} position(s)")
            
            for symbol, pos in self.positions.items():
                self.logger.debug(
                    f"Position: {symbol} | Qty: {pos['qty']}, "
                    f"Value: ${pos['market_value']:.2f}, "
                    f"P/L: ${pos['unrealized_pl']:.2f}"
                )
        else:
            self.logger.info("Portfolio update complete | No open positions")

    def get_position_qty(self, symbol: str) -> int:
        """Get quantity of shares held for a symbol"""
        qty = self.positions.get(symbol, {}).get('qty', 0)
        self.logger.debug(f"Position quantity for {symbol}: {qty}")
        return qty