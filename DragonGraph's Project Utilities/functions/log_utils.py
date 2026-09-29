"""Rotating-file logging and small formatting helpers.

The logging setup is shared so every maintainer tool writes the same shape of
log line to the same kind of rotating file, with sizes and retention read from
``.env``.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from functions import env_utils

LOG_MAX_BYTES = env_utils.get_int("LOG_MAX_BYTES", 1_000_000)
LOG_BACKUP_COUNT = env_utils.get_int("LOG_BACKUP_COUNT", 5)
LOG_LEVEL = env_utils.get_str("LOG_LEVEL", "DEBUG").upper()
LOG_FORMAT = env_utils.get_str("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")
CONSOLE_LOG_LEVEL = env_utils.get_str("CONSOLE_LOG_LEVEL", "DEBUG").upper()

_MIB = 1024 * 1024


def fmt_size(num_bytes: int) -> str:
    """Format a byte count into a short human-readable string."""
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < _MIB:
        return f"{num_bytes / 1024:.1f} KiB"
    return f"{num_bytes / _MIB:.1f} MiB"


def setup_logging(name: str, log_file: Path) -> logging.Logger:
    """Console + rotating-file logger, configured entirely from ``.env``."""
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(LOG_FORMAT)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(CONSOLE_LOG_LEVEL)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
