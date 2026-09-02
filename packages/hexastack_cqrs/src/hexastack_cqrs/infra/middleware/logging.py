from typing import Any

from hexastack_core.domain import Generic
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort
from hexastack_core.ports.logging import LoggingPort
from hexastack_cqrs.infra.config import LoggingMiddlewareConfig
from hexastack_cqrs.infra.middleware.generic import InOutMiddleware


class LoggingMiddleware(InOutMiddleware):
    """Middleware logging Generic message details and execution outcomes.

    Notes/Architectural Intent:
        Inherits from InOutMiddleware to emit structured log messages before and
        after handler execution, capturing message type and payload attributes
        through the LoggingPort interface. Supports dynamic feature flag evaluation
        via FeatureFlagPort.
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

    def before(self, instance: Generic) -> Any:
        """Log message details before execution if logging is enabled.

        Args:
            instance: Dispatched command or query message instance.

        Returns:
            Dictionary context containing message metadata and active flag status.
        """
        if not self._config.enable:
            return {"active": False}

        if self._flags is not None:
            eval_ctx = EvaluationContext.from_current_context()
            if not self._flags.is_enabled(
                "features.cqrs.logging", default=True, context=eval_ctx
            ):
                return {"active": False}

        message_name = instance.__class__.__name__
        extra: dict[str, Any] = {"message_type": message_name}

        if self._config.log_payload and hasattr(instance, "model_dump"):
            extra["payload"] = instance.model_dump()

        self._logger.info(f"Processing {message_name}", extra=extra)
        return {"active": True, "message_name": message_name}

    def after(self, instance: Generic, result: Any, context: Any) -> Any:
        """Log successful completion if logging was active.

        Args:
            instance: Dispatched command or query message instance.
            result: Result returned by downstream handler.
            context: Metadata dictionary returned by before().

        Returns:
            Unmodified result from downstream processing.
        """
        if isinstance(context, dict) and context.get("active"):
            message_name = context.get("message_name", instance.__class__.__name__)
            self._logger.debug(
                f"Successfully completed {message_name}",
                extra={"message_type": message_name},
            )
        return result

    def on_error(self, instance: Generic, exc: Exception, context: Any) -> None:
        """Log execution failure if logging was active.

        Args:
            instance: Dispatched command or query message instance.
            exc: Exception raised during execution.
            context: Metadata dictionary returned by before().
        """
        if isinstance(context, dict) and context.get("active"):
            message_name = context.get("message_name", instance.__class__.__name__)
            self._logger.error(
                f"Failed processing {message_name}: {exc}",
                extra={"message_type": message_name},
                exc=exc,
            )


__all__ = [
    "LoggingMiddleware",
]
