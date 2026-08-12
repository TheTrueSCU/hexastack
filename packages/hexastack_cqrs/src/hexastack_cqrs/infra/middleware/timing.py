import inspect
import time
from collections.abc import Callable
from typing import Any, cast

from hexastack_core.domain import Generic
from hexastack_core.ports.logging import LoggingPort

from hexastack_cqrs.infra.config import TimingMiddlewareConfig


class TimingMiddleware:
    """Middleware measuring execution time and logging warnings for slow commands.

    Notes/Architectural Intent:
        Captures high-resolution execution duration using perf_counter, recording
        duration metrics and warning on commands exceeding configured performance limits.
        Supports both synchronous handlers and asynchronous coroutines.
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

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Measure next_call execution time and log elapsed duration with slow warnings.

        Args:
            instance: The command or query Generic message instance.
            next_call: Callable representing the remaining middleware/handler chain.

        Returns:
            The result returned by next_call of type R (or an async coroutine if next_call is async).

        Raises:
            Exception: Propagates any error raised during handler execution after duration logging.
        """
        message_name = instance.__class__.__name__
        start_time = time.perf_counter()

        result = next_call(instance)

        if inspect.iscoroutine(result):

            async def _async_wrapped() -> Any:
                try:
                    return await result
                finally:
                    duration = time.perf_counter() - start_time
                    self._log_duration(message_name, duration)

            return cast(R, _async_wrapped())

        duration = time.perf_counter() - start_time
        self._log_duration(message_name, duration)
        return result
