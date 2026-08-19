from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hexastack_core.domain.generic import Generic
from hexastack_core.utils.context import get_user_context


class FlagEvaluationReason(StrEnum):
    """Reason explaining how a feature flag evaluation was resolved."""

    STATIC = "STATIC"
    DEFAULT = "DEFAULT"
    TARGETING_MATCH = "TARGETING_MATCH"
    SPLIT = "SPLIT"
    CACHED = "CACHED"
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"
    ERROR = "ERROR"


class EvaluationContext(Generic):
    """Contextual metadata provided for contextual feature flag evaluations.

    Notes/Architectural Intent:
        Encapsulates targeting key, user identifier, tenant partition, and
        custom arbitrary attributes matching the OpenFeature CNCF evaluation specification.
        Can be automatically constructed from the current ambient UserContext.
    """

    targeting_key: str | None = None
    user_id: str | None = None
    tenant_id: str | None = None
    roles: tuple[str, ...] = ()
    attributes: dict[str, Any] = {}

    @classmethod
    def from_current_context(cls, **extra_attributes: Any) -> "EvaluationContext":
        """Construct EvaluationContext from the ambient UserContext if available.

        Args:
            **extra_attributes: Additional key-value attributes to attach.

        Returns:
            EvaluationContext initialized with current user/tenant information.
        """
        user_ctx = get_user_context()
        if user_ctx is None:
            return cls(attributes=extra_attributes)

        return cls(
            targeting_key=user_ctx.user_id or user_ctx.tenant_id,
            user_id=user_ctx.user_id,
            tenant_id=user_ctx.tenant_id,
            roles=tuple(sorted(user_ctx.roles)),
            attributes=dict(extra_attributes),
        )


@dataclass(frozen=True)
class FlagEvaluationDetails[T]:
    """Detailed result of a feature flag evaluation.

    Notes/Architectural Intent:
        Matches OpenFeature FlagEvaluationDetails structure providing value,
        resolution reason, variant identifier, and optional error information.
    """

    flag_key: str
    value: T
    reason: FlagEvaluationReason = FlagEvaluationReason.UNKNOWN
    variant: str | None = None
    error_code: str | None = None
    error_message: str | None = None


__all__ = [
    "EvaluationContext",
    "FlagEvaluationDetails",
    "FlagEvaluationReason",
]
