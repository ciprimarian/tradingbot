# config/settings.py

import os
from dotenv import load_dotenv

#This line finds and loads the .env file in the project's root directory
load_dotenv()

#ALPACA API SETTINGS
# Load API key and secret from environment variables
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

# Determine if the mode is paper trading and set the correct URL
IS_PAPER_TRADING = os.getenv('IS_PAPER_TRADING', 'True').lower() in ('true', '1', 't')

if IS_PAPER_TRADING:
    BASE_URL = 'https://paper-api.alpaca.markets'
else:
    BASE_URL = 'https://api.alpaca.markets'

    # Check if the API keys are loaded correctly
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in the .env file.")