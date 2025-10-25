# tests/test_brokers.py

from src.brokers.alpaca_broker import AlpacaBroker

def connection_test():
    print("Running connection test to Alpaca...")
    broker = AlpacaBroker()
    account_info = broker.get_account_info()

    assert account_info is not None, "Failed to connect to Alpaca."
    assert 'id' in account_info, "Account info is missing"

    print("Connection test completed.")