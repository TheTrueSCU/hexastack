from collections.abc import Callable
from typing import Any

from hexastack_core.domain import Generic, HexastackError
from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_core.ports.feature_flags import FeatureFlagPort


class FeatureFlagDisabledError(HexastackError):
    """Exception raised when an execution is attempted on a disabled feature flag without a fallback."""


class ConditionalFeatureFlagMiddleware:
    """Middleware gating downstream execution or wrapping middleware based on a FeatureFlagPort evaluation.

    Notes/Architectural Intent:
        Evaluates a specified flag key against the ambient or provided `FeatureFlagPort`.
        If enabled, proceeds through the target middleware/handler chain; if disabled,
        either delegates to an optional fallback callable, bypasses, or raises FeatureFlagDisabledError.
    """

    def __init__(
        self,
        flags: FeatureFlagPort,
        flag_key: str,
        *,
        default: bool = False,
        fallback: Callable[[Any], Any] | None = None,
        bypass_on_disabled: bool = True,
    ) -> None:
        """Initialize conditional feature flag middleware.

        Args:
            flags: FeatureFlagPort implementation.
            flag_key: Feature flag identifier to evaluate.
            default: Fallback boolean value if flag is not explicitly resolved.
            fallback: Optional handler callable to execute if flag is disabled.
            bypass_on_disabled: If True and no fallback provided, bypasses to next_call.
                If False and no fallback provided, raises FeatureFlagDisabledError.
        """
        self._flags = flags
        self._flag_key = flag_key
        self._default = default
        self._fallback = fallback
        self._bypass_on_disabled = bypass_on_disabled

    def __call__[G: Generic, R](self, instance: G, next_call: Callable[[G], R]) -> R:
        """Evaluate feature flag and conditionally execute or bypass next_call.

        Args:
            instance: Command, query, or generic domain message.
            next_call: Callable downstream in execution pipeline.

        Returns:
            Result of next_call, fallback result, or raises error.
        """
        eval_ctx = EvaluationContext.from_current_context()
        is_active = self._flags.is_enabled(
            self._flag_key,
            default=self._default,
            context=eval_ctx,
        )

        if is_active:
            return next_call(instance)

        if self._fallback is not None:
            return self._fallback(instance)

        if self._bypass_on_disabled:
            return next_call(instance)

        raise FeatureFlagDisabledError(
            f"Feature flag '{self._flag_key}' is disabled for current context."
        )


__all__ = [
    "ConditionalFeatureFlagMiddleware",
    "FeatureFlagDisabledError",
]
