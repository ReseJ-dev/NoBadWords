"""Desktop application configuration."""

import logging

DEFAULT_LOG_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(level: int = DEFAULT_LOG_LEVEL) -> None:
    """Configure application-wide logging."""
    logging.basicConfig(level=level, format=LOG_FORMAT)

