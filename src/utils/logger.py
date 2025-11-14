#src/utils/logger.py

import logging 
import logging.config
from pathlib import Path
from typing import Optional

DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": str(
                Path(__file__).resolve().parents[2] / "logs" / "trading_bot.log"
            ),
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

_LOGGING_CONFIGURED = False


def configure_logging(config: Optional[dict] = None):
    global _LOGGING_CONFIGURED
    if  _LOGGING_CONFIGURED:
        return
    
    config_dict = config or DEFAULT_LOGGING_CONFIG
    log_file = Path(config_dict["handlers"]["file"]["filename"])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(config_dict)
    _LOGGING_CONFIGURED = True

def get_logger(name: Optional[str] = None) -> logging.Logger:
     configure_logging()
     return logging.getLogger(name or "trading_bot")