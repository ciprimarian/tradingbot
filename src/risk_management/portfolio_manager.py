from src.brokers.alpaca_broker import AlpacaBroker

class PortfolioManager:
    def __init__(self, broker: AlpacaBroker):
        self.broker = broker
        self.cash = 0.0
        self.portfolio_value = 0.0
        self.positions = {} #A dictionary to store positions by symbol
        self.update_portfolio() #Initial fetch during creation

    def update_portfolio(self):
        print("Updating portfolio state...")
        account_info = self.broker.get_account_info()
        if account_info:
            self.cash = float(account_info.get('cash', 0.0))
            self.portfolio_value = float(account_info.get('portfolio_value', 0.0))

        open_positions = self.broker.get_open_positions()
        self.positions = {} #Clear old positions
        if open_positions:
            for position in open_positions:
                symbol = position.get('symbol')
                if symbol:
                    self.positions[symbol] = {
                        'qty': int(position.get('qty', 0.0)),
                        'market_value': float(position.get('market_value', 0.0)),
                        'unrealized_pl': float(position.get('unrealized_pl', 0.0))
                    }
        print("Portfolio update complete")

    def get_position_qty(self, symbol: str) -> int:
        return self.positions.get(symbol, {}).get('qty', 0) #Return 0 if the symbol is not in the portfolio.