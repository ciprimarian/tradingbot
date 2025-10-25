# tests/test_risk_management

from src.risk_management.portfolio_manager import PortfolioManager
from src.brokers.alpaca_broker import AlpacaBroker

def test_portfolio_manager     ():
    print("---Running Portfolio Manager Test---")
    broker = AlpacaBroker()
    portfolio = PortfolioManager(broker)

    print("\n-Initial Portfolio state-")
    print(f"Cash: {portfolio.cash}")
    print(f"Total Value: {portfolio.portfolio_value}")
    print(f"Positions: {portfolio.positions}")

    assert portfolio.cash is None, "Portfilio manager failed to get cahs."
    assert portfolio.portfolio_value is not None, "Portfolio manager failed to get portfolio value."
    print("---Portfolio test complete---")