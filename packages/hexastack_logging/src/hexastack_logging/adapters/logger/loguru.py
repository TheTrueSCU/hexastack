import importlib
from typing import Any

from hexastack_core.ports.logging import Extras, LoggingPort
from hexastack_core.utils.context import get_correlation_id, get_user_context


class LoguruAdapter(LoggingPort):
    """Optional Loguru adapter implementing LoggingPort.

    Notes/Architectural Intent:
        Delegates logging to loguru while binding Hexastack correlation
        and user context.
    """

    def __init__(self, logger: Any = None) -> None:
        """Initialize LoguruAdapter.

        Args:
            logger: Optional loguru logger instance.

        Raises:
            ImportError: If loguru package is not installed.
        """
        if logger is None:
            try:
                loguru_mod = importlib.import_module("loguru")
                self._logger: Any = loguru_mod.logger
            except ImportError as err:
                raise ImportError(
                    "loguru is required for LoguruAdapter. Install via 'pip install hexastack-logging[loguru]'."
                ) from err
        else:
            self._logger = logger

    def _get_bound_logger(self, extra: Extras | None = None) -> Any:
        bind_dict: dict[str, Any] = dict(extra) if extra else {}
        cid = get_correlation_id()
        if cid:
            bind_dict["correlation_id"] = cid
        user = get_user_context()
        if user:
            bind_dict["user_id"] = user.user_id
            if user.tenant_id:
                bind_dict["tenant_id"] = user.tenant_id
        return self._logger.bind(**bind_dict)

    def critical(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log a critical message through loguru.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        log = self._get_bound_logger(extra)
        log.opt(exception=exc).critical(message)

    def debug(self, message: str, extra: Extras | None = None) -> None:
        """Log a debug message through loguru.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        log = self._get_bound_logger(extra)
        log.debug(message)

    def error(
        self, message: str, extra: Extras | None = None, exc: Exception | None = None
    ) -> None:
        """Log an error message through loguru.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.
            exc: Optional exception instance to attach traceback.

        Returns:
            None.

        Raises:
            None.
        """
        log = self._get_bound_logger(extra)
        log.opt(exception=exc).error(message)

    def info(self, message: str, extra: Extras | None = None) -> None:
        """Log an informational message through loguru.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        log = self._get_bound_logger(extra)
        log.info(message)

    def warning(self, message: str, extra: Extras | None = None) -> None:
        """Log a warning message through loguru.

        Args:
            message: Text message to log.
            extra: Optional key-value dictionary of contextual metadata.

        Returns:
            None.

        Raises:
            None.
        """
        log = self._get_bound_logger(extra)
        log.warning(message)
