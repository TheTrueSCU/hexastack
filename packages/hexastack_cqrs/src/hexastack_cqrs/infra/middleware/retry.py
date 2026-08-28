from collections.abc import Callable

import stamina
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    retry_if_not_exception_type,
    stop_after_attempt,
)

from hexastack_core.domain import Generic, HexastackError
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.config import RetryMiddlewareConfig


def _should_stamina_retry(exc: Exception) -> bool:
    """Predicate indicating whether stamina should retry an exception.

    Args:
        exc: Exception raised during execution.

    Returns:
        False if exc is a deterministic HexastackError, True otherwise.
    """
    return not isinstance(exc, HexastackError)


class StaminaRetryMiddleware:
    """Resilience middleware executing handler calls with stamina automatic retries and backoff.

    Notes/Architectural Intent:
        Uses stamina for exponential backoff with full jitter and telemetry hooks.
        Skips retries on explicit Hexastack domain errors (HexastackError) and logs
        transient attempt failures via LoggingPort without tight telemetry coupling.
    """

    def __init__(
        self,
        logger: LoggingPort | None = None,
        config: RetryMiddlewareConfig | None = None,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize stamina retry middleware with optional logger, config, and flags.

        Args:
            logger: Optional LoggingPort instance to receive retry debug messages.
            config: Optional RetryMiddlewareConfig providing retry attempts and backoff bounds.
            flags: Optional FeatureFlagPort to dynamically evaluate retry activation.
        """
        self._logger = logger
        self._config = config or RetryMiddlewareConfig()
        self._flags = flags

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Execute next_call with stamina retry backoff policies.

        Args:
            instance: The command or query message instance.
            next_call: Callable executing downstream handler logic.

        Returns:
            The result returned by next_call.

        Raises:
            Exception: If retries are exhausted or non-retryable domain error occurs.
        """
        if not self._config.enable:
            return next_call(instance)

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.cqrs.retry", default=True, context=eval_ctx
            ):
                return next_call(instance)

        attempts = 0
        message_name = instance.__class__.__name__

        for attempt in stamina.retry_context(
            on=_should_stamina_retry,
            attempts=self._config.max_attempts,
            wait_initial=self._config.initial_backoff_seconds,
            wait_max=self._config.max_backoff_seconds,
            wait_jitter=self._config.initial_backoff_seconds
            if self._config.jitter
            else 0.0,
        ):
            with attempt:
                attempts += 1
                try:
                    return next_call(instance)
                except Exception as exc:
                    if (
                        self._logger
                        and attempts < self._config.max_attempts
                        and _should_stamina_retry(exc)
                    ):
                        self._logger.debug(
                            f"Stamina retrying {message_name} (attempt {attempts}/{self._config.max_attempts}) after transient error: {exc}",
                            extra={
                                "message_type": message_name,
                                "attempt": attempts,
                                "max_attempts": self._config.max_attempts,
                            },
                        )
                    raise

        msg = f"Stamina retry failed to execute {message_name}"
        raise RuntimeError(msg)


class TenacityRetryMiddleware:
    """Middleware executing handler calls with tenacity automatic retries and debug logging.

    Notes/Architectural Intent:
        Provides resilience against transient failures during command/query execution,
        skipping retries on explicit Hexastack domain errors and logging retry state.
        Respects dynamic feature flag evaluation via FeatureFlagPort.
    """

    def __init__(
        self,
        logger: LoggingPort | None = None,
        config: RetryMiddlewareConfig | None = None,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize retry middleware with optional logger, retry configuration, and flags.

        Args:
            logger: Optional LoggingPort instance to receive retry debug messages.
            config: Optional RetryMiddlewareConfig providing retry attempts and toggles.
            flags: Optional FeatureFlagPort to dynamically evaluate retry activation.
        """
        self._logger = logger
        self._config = config or RetryMiddlewareConfig()
        self._flags = flags

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

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.cqrs.retry", default=True, context=eval_ctx
            ):
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


__all__ = [
    "StaminaRetryMiddleware",
    "TenacityRetryMiddleware",
]
