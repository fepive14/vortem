"""Structured logging configuration via structlog.

In production:  JSON output (machine-readable, log-aggregator friendly).
In development: colored, human-readable console output.

Every log entry automatically includes `request_id` when set in context.
"""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import EventDict, Processor


def _add_log_level(logger: object, method: str, event_dict: EventDict) -> EventDict:
    """Ensure 'level' key is present for processors that need it."""
    if "level" not in event_dict:
        event_dict["level"] = method.upper()
    return event_dict


def configure_logging(environment: str, log_level: str) -> None:
    """Set up structlog and stdlib logging.

    Call once at application startup before any logging takes place.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)
    is_production = environment == "production"

    # Shared processors run on every log record regardless of renderer.
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        _add_log_level,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_production:
        # JSON renderer — all keys are serialised to JSON.
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        # Pretty console renderer for local development.
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *shared_processors,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    # Silence noisy third-party loggers.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger."""
    return structlog.get_logger(name)
