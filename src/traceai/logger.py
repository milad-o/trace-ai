"""Central logging configuration for TraceAI."""

from __future__ import annotations

import logging
import logging.config
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_CONFIGURED = False
_LOGGER_NAME = "traceai"


def _resolve_logs_dir() -> Path:
    root_dir = Path(__file__).resolve().parents[2]
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def _configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = os.getenv("TRACEAI_LOG_LEVEL", "INFO").upper()
    logs_dir = _resolve_logs_dir()

    log_format = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": log_format,
                    "datefmt": date_format,
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": log_level,
                    "formatter": "standard",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": log_level,
                    "formatter": "standard",
                    "filename": str(logs_dir / "traceai.log"),
                    "maxBytes": 5 * 1024 * 1024,
                    "backupCount": 5,
                    "encoding": "utf-8",
                },
            },
            "root": {
                "level": log_level,
                "handlers": ["console", "file"],
            },
        }
    )

    # Suppress verbose third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger (child loggers inherit global config)."""
    _configure_logging()
    logger_name = name or _LOGGER_NAME
    return logging.getLogger(logger_name)


# Eagerly configure and expose the default TraceAI logger
_configure_logging()
logger = logging.getLogger(_LOGGER_NAME)


__all__ = ["logger", "get_logger"]
