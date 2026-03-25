"""
Logging configuration — call setup_logging() once at application startup.
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "logs"


def setup_logging(level: str = "INFO", log_to_file: bool = False) -> logging.Logger:
    """
    Configure root logger with console output (and optionally file output).
    Returns the root logger.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Use a stream that replaces unencodable chars (e.g. Medium article titles
    # with hair spaces, em dashes, smart quotes on Windows cp1252 consoles)
    safe_stream = open(  # noqa: SIM115
        sys.stdout.fileno(), mode="w", encoding="utf-8", errors="replace", closefd=False
    )

    handlers: list[logging.Handler] = [
        logging.StreamHandler(safe_stream),
    ]

    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
        handlers.append(file_handler)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logging.getLogger()
