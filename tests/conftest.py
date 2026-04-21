"""Pytest configuration — stubs external credentials so tests collect without live API keys."""
import os

os.environ.setdefault("ALPACA_API_KEY", "test-key-stub")
os.environ.setdefault("ALPACA_SECRET_KEY", "test-secret-stub")
