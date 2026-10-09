
import logging

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure application logging in JSON format."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(
            fmt="iso",
            utc=True,
            key="timestamp",
        ),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Return a structured logger."""
    return structlog.get_logger(name)
