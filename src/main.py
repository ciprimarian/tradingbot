from brokers.alpaca_broker import AlpacaBroker

def run_connection_test():
    print("Running connection test to Alpaca...")
    broker = AlpacaBroker()
    broker.get_account_info()
    print("Connection test completed.")

if __name__ == "__main__":
    run_connection_test()