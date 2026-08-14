from collections.abc import Callable

from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
)

from hexastack_core.domain import Generic, HexastackError
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.config import RetryMiddlewareConfig


class TenacityRetryMiddleware:
    """Middleware executing handler calls with tenacity automatic retries and debug logging.

    Notes/Architectural Intent:
        Provides resilience against transient failures during command/query execution,
        skipping retries on explicit Hexastack domain errors and logging retry state.
    """

    def __init__(
        self,
        logger: LoggingPort | None = None,
        config: RetryMiddlewareConfig | None = None,
    ) -> None:
        """Initialize retry middleware with optional logger and retry configuration.

        Args:
            logger: Optional LoggingPort instance to receive retry debug messages.
            config: Optional RetryMiddlewareConfig providing retry attempts and toggles.
        """
        self._logger = logger
        self._config = config or RetryMiddlewareConfig()

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Execute next_call with retry policies and debug logging.

        Args:
            instance: The command or query message instance.
            next_call: Callable executing downstream handler logic.

        Returns:
            The result returned by next_call.

        Raises:
            Exception: If retries are exhausted or non-retryable exception occurs.
        """
        if not self._config.enable:
            return next_call(instance)

        message_name = instance.__class__.__name__

        def _before_sleep(retry_state: RetryCallState) -> None:
            if self._logger:
                attempt = retry_state.attempt_number
                outcome = retry_state.outcome
                exc_str = outcome.exception() if outcome else "unknown error"
                self._logger.debug(
                    f"Retrying {message_name} (attempt {attempt}/{self._config.max_attempts}) after error: {exc_str}",
                    extra={
                        "message_type": message_name,
                        "attempt": attempt,
                        "max_attempts": self._config.max_attempts,
                    },
                )

        @retry(
            reraise=True,
            retry=(
                retry_if_exception_type(Exception)
                & retry_if_not_exception_type(HexastackError)
            ),
            stop=stop_after_attempt(self._config.max_attempts),
            before_sleep=_before_sleep,
        )
        def _next_call_with_retry() -> R:
            return next_call(instance)

        return _next_call_with_retry()
