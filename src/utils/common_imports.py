# src/utils/common_imports.py

"""
Common imports used across the trading bot codebase.
Import from here to reduce repetition and maintain consistency.
"""

# Data manipulation libraries (used in 90% of files)
import pandas as pd
import numpy as np

# Type hints (used everywhere)
from typing import Dict, List, Optional, Any, Union, Tuple

# Project-specific common imports
from src.utils.logger import get_logger

__all__ = [
    # Data libraries
    'pd',
    'np',
    
    # Type hints
    'Dict',
    'List',
    'Optional',
    'Any',
    'Union',
    'Tuple',
    
    # Utilities
    'get_logger',
]
