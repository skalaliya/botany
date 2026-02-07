from __future__ import annotations

import json
import logging
from typing import Any

from libs.common.tracing import get_trace_id

SENSITIVE_KEYS = {
    "password",
    "token",
    "authorization",
    "ssn",
    "email",
    "phone",
    "address",
    "refresh_token",
}


class PiiSafeJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "event") and isinstance(record.event, dict):
            payload["event"] = self._redact(record.event)
        return json.dumps(payload, default=str)

    def _redact(self, payload: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key, value in payload.items():
            if key.lower() in SENSITIVE_KEYS:
                safe[key] = "[REDACTED]"
            elif isinstance(value, dict):
                safe[key] = self._redact(value)
            else:
                safe[key] = value
        return safe


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("nexuscargo")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(PiiSafeJsonFormatter())
    logger.addHandler(handler)
    return logger


def log_event(logger: logging.Logger, message: str, event: dict[str, Any]) -> None:
    enriched_event = dict(event)
    enriched_event.setdefault("trace_id", get_trace_id())
    logger.info(message, extra={"event": enriched_event})
