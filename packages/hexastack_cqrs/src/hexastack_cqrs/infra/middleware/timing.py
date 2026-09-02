import time
from typing import Any

from hexastack_core.domain import Generic
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.config import TimingMiddlewareConfig
from hexastack_cqrs.infra.middleware.generic import InOutMiddleware


class TimingMiddleware(InOutMiddleware):
    """Middleware measuring execution time and logging warnings for slow commands.

    Notes/Architectural Intent:
        Inherits from InOutMiddleware to capture execution duration using perf_counter,
        recording duration metrics and warning on commands exceeding configured performance
        limits for both synchronous and asynchronous handlers.
    """

    def __init__(
        self,
        logger: LoggingPort,
        config: TimingMiddlewareConfig | None = None,
    ) -> None:
        """Initialize timing middleware with logger and configuration.

        Args:
            logger: LoggingPort instance to receive execution duration logs.
            config: Optional TimingMiddlewareConfig controlling slow thresholds and warnings.
        """
        self._logger = logger
        self._config = config or TimingMiddlewareConfig()

    def before(self, instance: Generic) -> Any:
        """Capture the start timestamp before downstream execution.

        Args:
            instance: Dispatched command or query message instance.

        Returns:
            Float start timestamp from time.perf_counter().
        """
        return time.perf_counter()

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        """Calculate elapsed duration and log timing summary upon successful completion.

        Args:
            instance: Dispatched command or query message instance.
            result: Result returned from downstream execution.
            context: Start timestamp float returned by before().

        Returns:
            Unmodified result from downstream processing.
        """
        duration = time.perf_counter() - float(context)
        self._log_duration(instance.__class__.__name__, duration)
        return result

    def on_error(self, instance: Generic, exc: Exception, context: Any) -> None:
        """Log elapsed duration when downstream execution raises an error.

        Args:
            instance: Dispatched command or query message instance.
            exc: Exception raised during execution.
            context: Start timestamp float returned by before().
        """
        if context is not None:
            duration = time.perf_counter() - float(context)
            self._log_duration(instance.__class__.__name__, duration)

    def _log_duration(self, message_name: str, duration: float) -> None:
        """Helper method to format and emit duration log records.

        Args:
            message_name: String name of the processed message class.
            duration: Elapsed execution time in seconds.
        """
        extra = {
            "message_type": message_name,
            "duration_seconds": duration,
        }

        if (
            self._config.enable_slow_warning
            and duration >= self._config.slow_threshold_seconds
        ):
            self._logger.warning(
                f"Slow execution detected for {message_name} ({duration:.4f}s >= {self._config.slow_threshold_seconds:.4f}s)",
                extra=extra,
            )
        else:
            self._logger.info(
                f"Executed {message_name} in {duration:.4f}s",
                extra=extra,
            )


__all__ = [
    "TimingMiddleware",
]
