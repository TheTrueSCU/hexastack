import logging

from hexastack_core.utils.context import (
    get_correlation_id,
    get_user_context,
)
from hexastack_logging.infra.sanitizer import Sanitizer


class CorrelationIdFilter(logging.Filter):
    """Logging filter enriching LogRecord instances with correlation and user context.

    Notes/Architectural Intent:
        Injects correlation_id, user_id, and tenant_id from ContextVar into standard
        library LogRecord attributes, ensuring uniform log formatting across internal
        and third-party framework logs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Enrich log record with active correlation ID and user metadata.

        Args:
            record: The LogRecord instance to inspect and mutate.

        Returns:
            Always True so the log record continues processing.

        Raises:
            None.
        """
        correlation_id = get_correlation_id()
        user = get_user_context()

        record.correlation_id = correlation_id  # type: ignore[attr-defined]
        record.user_id = user.user_id if user else None  # type: ignore[attr-defined]
        record.tenant_id = user.tenant_id if user else None  # type: ignore[attr-defined]

        return True


_STANDARD_LOG_RECORD_KEYS = frozenset(
    {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "correlation_id",
        "user_id",
        "tenant_id",
    }
)


class SanitizerFilter(logging.Filter):
    """Logging filter sanitizing sensitive keys, PII, and tokens from LogRecords.

    Notes/Architectural Intent:
        Intercepts LogRecord objects, scrubbing sensitive credentials from message strings,
        positional/keyword arguments, extra attributes, and formatted traceback text.
    """

    def __init__(self, sanitizer: Sanitizer | None = None) -> None:
        """Initialize SanitizerFilter with a Sanitizer instance.

        Args:
            sanitizer: Optional Sanitizer instance (defaults to standard Sanitizer).
        """
        super().__init__()
        self._sanitizer = sanitizer or Sanitizer()

    def _sanitize_extra_attributes(self, record: logging.LogRecord) -> None:
        """Scrub non-standard LogRecord dictionary attributes."""
        for key, value in list(record.__dict__.items()):
            if key not in _STANDARD_LOG_RECORD_KEYS:
                record.__dict__[key] = self._sanitizer.sanitize(value)

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize message, arguments, extra attributes, and tracebacks on log record.

        Args:
            record: The LogRecord instance to sanitize.

        Returns:
            Always True so the sanitized record continues processing.

        Raises:
            None.
        """
        # 1. Sanitize main message
        if isinstance(record.msg, str):
            record.msg = self._sanitizer.sanitize_string(record.msg)
        else:
            record.msg = self._sanitizer.sanitize(record.msg)

        # 2. Sanitize arguments
        if record.args:
            if isinstance(record.args, dict):
                record.args = self._sanitizer.sanitize_dict(record.args)
            elif isinstance(record.args, tuple):
                record.args = tuple(self._sanitizer.sanitize_list(list(record.args)))

        # 3. Sanitize extra attributes on record.__dict__
        self._sanitize_extra_attributes(record)

        # 4. Sanitize exc_text if present
        if record.exc_text:
            record.exc_text = self._sanitizer.sanitize_traceback(record.exc_text)

        return True


__all__ = [
    "CorrelationIdFilter",
    "SanitizerFilter",
]
