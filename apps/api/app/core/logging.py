"""Small JSON logging helpers shared by the API and the worker."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, TextIO

JOB_LOG_FIELDS = (
    "job_id",
    "team_profile_id",
    "fixture_id",
    "content_type",
    "provider",
    "duration_ms",
    "status",
)


class JsonFormatter(logging.Formatter):
    """Emit machine-readable logs while keeping API credentials out of messages."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _redact(str(record.getMessage())),
        }
        for field in JOB_LOG_FIELDS + ("method", "path", "error_type", "app_env", "warning"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


class JsonStreamHandler(logging.StreamHandler[TextIO]):
    _football_ai_json = True


def configure_logging(level: int = logging.INFO) -> None:
    """Install one JSON handler without disturbing an embedding server's handlers."""

    root = logging.getLogger()
    if any(getattr(handler, "_football_ai_json", False) for handler in root.handlers):
        return
    handler = JsonStreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


def _redact(message: str) -> str:
    """Avoid accidentally retaining common bearer/API-token shapes in diagnostics."""

    for marker in ("api_token=", "Authorization: Bearer "):
        start = message.lower().find(marker.lower())
        if start == -1:
            continue
        end = len(message)
        for separator in ("&", " ", "\n"):
            candidate = message.find(separator, start + len(marker))
            if candidate != -1:
                end = min(end, candidate)
        message = f"{message[: start + len(marker)]}[REDACTED]{message[end:]}"
    return message
