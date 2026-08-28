from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from hexastack_core.domain.feature_flags import (
    EvaluationContext,
    FlagEvaluationDetails,
)


@runtime_checkable
class FeatureFlagPort(Protocol):
    """Port interface for evaluating feature flags and dynamic configuration toggles.

    Notes/Architectural Intent:
        Defines an agnostic feature flagging port aligned with the CNCF OpenFeature standard.
        Can be backed by in-memory mappings, static configuration files, or external
        providers (OpenFeature / Flagd / Unleash / LaunchDarkly).
    """

    def get_boolean_details(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> FlagEvaluationDetails[bool]:
        """Evaluate a boolean feature flag with complete resolution metadata.

        Args:
            flag_key: Unique identifier of the feature flag.
            default: Fallback value if resolution fails.
            context: Optional EvaluationContext for targeting rules.

        Returns:
            FlagEvaluationDetails containing value, reason, and variant.
        """

    def get_boolean_value(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag (alias for is_enabled matching OpenFeature convention).

        Args:
            flag_key: Unique identifier of the feature flag.
            default: Fallback value if resolution fails or flag is missing.
            context: Optional EvaluationContext for targeting rules.

        Returns:
            Resolved boolean flag status.
        """

    def get_float_value(
        self,
        flag_key: str,
        default: float,
        context: EvaluationContext | None = None,
    ) -> float:
        """Evaluate a floating-point feature flag.

        Args:
            flag_key: Unique identifier of the feature flag.
            default: Fallback value if resolution fails.
            context: Optional EvaluationContext for targeting rules.

        Returns:
            Resolved float value.
        """

    def get_integer_value(
        self,
        flag_key: str,
        default: int,
        context: EvaluationContext | None = None,
    ) -> int:
        """Evaluate an integer feature flag / limit.

        Args:
            flag_key: Unique identifier of the feature flag.
            default: Fallback value if resolution fails.
            context: Optional EvaluationContext for targeting rules.

        Returns:
            Resolved integer value.
        """

    def get_object_value(
        self,
        flag_key: str,
        default: Mapping[str, Any],
        context: EvaluationContext | None = None,
    ) -> Mapping[str, Any]:
        """Evaluate a structured JSON/dictionary feature flag.

        Args:
            flag_key: Unique identifier of the feature flag.
            default: Fallback dictionary if resolution fails.
            context: Optional EvaluationContext for targeting rules.

        Returns:
            Resolved structured configuration.
        """

    def get_string_value(
        self,
        flag_key: str,
        default: str,
        context: EvaluationContext | None = None,
    ) -> str:
        """Evaluate a string feature flag / variant.

        Args:
            flag_key: Unique identifier of the feature flag.
            default: Fallback value if resolution fails.
            context: Optional EvaluationContext for targeting rules.

        Returns:
            Resolved string variation.
        """

    def is_enabled(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag.

        Args:
            flag_key: Unique identifier of the feature flag.
            default: Fallback value if resolution fails or flag is missing.
            context: Optional EvaluationContext for targeting rules.

        Returns:
            Resolved boolean flag status.
        """


__all__ = [
    "FeatureFlagPort",
]
