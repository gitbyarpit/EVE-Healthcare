"""
Structured JSON logging with per-request context.

Every log line is emitted as a single-line JSON object so that log aggregators
(CloudWatch, Datadog, ELK, etc.) can parse fields without custom grok patterns.
A ``request_id`` context variable is set by the middleware in ``main.py`` and
automatically included in every log entry for end-to-end request tracing.
"""

import json
import logging
import sys
from contextvars import ContextVar

# Stores the current request's unique ID; set by the ASGI middleware.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class JSONFormatter(logging.Formatter):
    """Formats each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(""),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Replace the root logger's handlers with a single JSON-to-stdout handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Reduce noise from framework internals
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger (thin convenience wrapper)."""
    return logging.getLogger(name)
