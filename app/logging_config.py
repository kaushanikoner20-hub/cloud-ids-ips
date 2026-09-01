"""
Structured logging configuration.
"""
import logging
import sys
from app.config import settings

def setup_logging():
    """
    Configure the application logging.
    """
    logging.basicConfig(
        level=settings.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    logging.info("Logging initialized")
