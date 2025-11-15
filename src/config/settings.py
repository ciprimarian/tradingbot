# config/settings.py

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

#This line finds and loads the .env file in the project's root directory
load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
#ALPACA API SETTINGS
# Load API key and secret from environment variables
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

# Determine if the mode is paper trading and set the correct URL
IS_PAPER_TRADING = os.getenv('ALPACA_PAPER_TRADING', 'True').lower() in ('true', '1', 't')

if IS_PAPER_TRADING:
    BASE_URL = 'https://paper-api.alpaca.markets'
else:
    BASE_URL = 'https://api.alpaca.markets'

    # Check if the API keys are loaded correctly
if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
    raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in the .env file.")

def load_config(config_path= PROJECT_ROOT /'src' / 'config' / 'trading_config.yaml'):
    """
    Loads the main YAML cofiguration file.
    """
    print(f"Loading cofiguration from {config_path}...")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found at path: {config_path}")
    except Exception as e:
        print(f"Error loading config file: {e}")
        return {}

#Load the configuration and make it available for other modules
CONFIG = load_config()        