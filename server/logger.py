"""
Central logging configuration for the Lunar Rover server.

Import and call ``setup_logging()`` once at startup.  All modules in the
project then use ``logging.getLogger(__name__)`` and the output is
formatted consistently.
"""
import logging
import sys


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a clean, informative format."""
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# Module-level logger for any code that imports this file directly
log = logging.getLogger(__name__)
