import inspect
from collections.abc import Callable
from typing import Any, cast

from hexastack_core.domain import Generic
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.config import LoggingMiddlewareConfig


class LoggingMiddleware:
    """Middleware logging Generic message details and execution outcomes.

    Notes/Architectural Intent:
        Emits structured log messages before and after handler execution, capturing
        message type and payload attributes through the LoggingPort interface.
        Supports both synchronous handlers and asynchronous coroutines, and respects
        dynamic feature flag evaluation via FeatureFlagPort.
    """

    def __init__(
        self,
        logger: LoggingPort,
        config: LoggingMiddlewareConfig | None = None,
        flags: FeatureFlagPort | None = None,
    ) -> None:
        """Initialize logging middleware with logger, configuration, and optional feature flags.

        Args:
            logger: LoggingPort instance to receive structured log messages.
            config: Optional LoggingMiddlewareConfig controlling logging behavior.
            flags: Optional FeatureFlagPort to dynamically evaluate logging activation.
        """
        self._logger = logger
        self._config = config or LoggingMiddlewareConfig()
        self._flags = flags

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Log message details, invoke downstream handler, and log outcome.

        Args:
            instance: The command or query Generic message instance.
            next_call: Callable representing the remaining middleware/handler chain.

        Returns:
            The result returned by next_call of type R (or an async coroutine if next_call is async).

        Raises:
            Exception: Propagates any error raised during handler execution after error logging.
        """
        if not self._config.enable:
            return next_call(instance)

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.cqrs.logging", default=True, context=eval_ctx
            ):
                return next_call(instance)

        message_name = instance.__class__.__name__
        extra: dict[str, Any] = {"message_type": message_name}

        if self._config.log_payload:
            extra["payload"] = instance.model_dump()

        self._logger.info(f"Processing {message_name}", extra=extra)

        try:
            result = next_call(instance)
        except Exception as exc:
            self._logger.error(
                f"Failed processing {message_name}: {exc}",
                extra={"message_type": message_name},
                exc=exc,
            )
            raise

        if inspect.iscoroutine(result):

            async def _async_wrapped() -> Any:
                try:
                    async_res = await result
                    self._logger.debug(
                        f"Successfully completed {message_name}",
                        extra={"message_type": message_name},
                    )
                    return async_res
                except Exception as async_exc:
                    self._logger.error(
                        f"Failed processing {message_name}: {async_exc}",
                        extra={"message_type": message_name},
                        exc=async_exc,
                    )
                    raise

            return cast("R", _async_wrapped())

        self._logger.debug(
            f"Successfully completed {message_name}",
            extra={"message_type": message_name},
        )
        return result
