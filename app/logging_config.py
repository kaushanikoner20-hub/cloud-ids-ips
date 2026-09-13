"""Structured JSON logging setup.

Per ARCHITECTURE.md Section 1.7 / 13: structured JSON logs, no secrets in
logs. This module configures the root logger once at application startup.
"""

import logging
import sys

try:  # python-json-logger >= 3.0
    from pythonjsonlogger.json import JsonFormatter
except ImportError:  # python-json-logger < 3.0
    from pythonjsonlogger.jsonlogger import JsonFormatter


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    # Avoid duplicate handlers if configure_logging() is called more than
    # once (e.g. under the test client / reload).
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet noisy third-party loggers at DEBUG unless explicitly requested.
    if level.upper() != "DEBUG":
        logging.getLogger("uvicorn.access").setLevel("WARNING")