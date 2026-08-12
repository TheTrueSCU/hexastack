import importlib
from typing import Any

from hexastack_core.ports.logging import Extras, LoggingPort
from hexastack_core.utils.context import get_correlation_id, get_user_context


class StructlogAdapter(LoggingPort):
    """Optional Structlog adapter implementing LoggingPort.

    Notes/Architectural Intent:
        Delegates logging to structlog BoundLogger while binding Hexastack correlation
        and user context.
    """

    def __init__(self, logger: Any = None) -> None:
        """Initialize StructlogAdapter.

        Args:
            logger: Optional structlog logger instance.

        Raises:
            ImportError: If structlog package is not installed.
        """
        if logger is None:
            try:
                structlog_mod = importlib.import_module("structlog")
                self._logger: Any = structlog_mod.get_logger()
            except ImportError as err:
                raise ImportError(
                    "structlog is required for StructlogAdapter. Install via 'pip install hexastack-logging[structlog]'."
                ) from err
        else:
            self._logger = logger

    def _bind_context(self, extra: Extras | None = None) -> dict[str, Any]:
        context: dict[str, Any] = dict(extra) if extra else {}
        cid = get_correlation_id()
        if cid:
            context["correlation_id"] = cid
        user = get_user_context()
        if user:
            context["user_id"] = user.user_id
            if user.tenant_id:
                context["tenant_id"] = user.tenant_id
        return context

    def critical(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log a critical message through structlog.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.critical(message, exc_info=exc, **self._bind_context(extra))

    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Log a debug message through structlog.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.debug(message, **self._bind_context(extra))

    def error(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log an error message through structlog.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.error(message, exc_info=exc, **self._bind_context(extra))

    def info(self, message: str, extra: Extras | None = None) -> None:
        """Log an informational message through structlog.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.info(message, **self._bind_context(extra))

    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Log a warning message through structlog.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        self._logger.warning(message, **self._bind_context(extra))
