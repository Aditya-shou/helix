"""
logging_config.py
-----------------
Call setup_logging() once at startup (in main.py) and every module
that uses logging.getLogger(__name__) will inherit the correct config.
"""

import logging
import sys

from agent.config import settings


def setup_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%H:%M:%S"

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers if called more than once
    if not root.handlers:
        root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "anthropic", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
