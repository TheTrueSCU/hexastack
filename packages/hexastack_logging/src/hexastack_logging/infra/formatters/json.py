import json
import logging
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    """High-performance JSON log formatter for structured production logging.

    Notes/Architectural Intent:
        Formats LogRecord instances into single-line JSON objects with ISO 8601 UTC
        timestamps, context tracking identifiers, and structured metadata.
    """

    def __init__(self, include_context: bool = True) -> None:
        """Initialize JsonFormatter.

        Args:
            include_context: If True, serializes correlation_id, user_id, and tenant_id.
        """
        super().__init__()
        self._include_context = include_context

    def format(self, record: logging.LogRecord) -> str:
        """Format the specified record as a JSON string.

        Args:
            record: The LogRecord to format.

        Returns:
            JSON-encoded log line string.

        Raises:
            None.
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if self._include_context:
            log_data["correlation_id"] = getattr(record, "correlation_id", "")
            log_data["user_id"] = getattr(record, "user_id", None)
            log_data["tenant_id"] = getattr(record, "tenant_id", None)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)
