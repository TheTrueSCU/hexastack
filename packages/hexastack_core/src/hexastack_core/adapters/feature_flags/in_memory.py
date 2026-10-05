from collections.abc import Mapping
from typing import Any

from hexastack_core.domain.feature_flags import (
    EvaluationContext,
    FlagEvaluationDetails,
    FlagEvaluationReason,
)
from hexastack_core.ports.feature_flags import FeatureFlagPort


class InMemoryFeatureFlagAdapter(FeatureFlagPort):
    """In-memory dictionary-backed feature flag adapter.

    Notes/Architectural Intent:
        Provides a zero-dependency default for local development, fast unit testing,
        and static fallback flag evaluation without requiring external flag servers.
    """

    def __init__(self, flags: Mapping[str, Any] | None = None) -> None:
        """Initialize adapter with initial flag mapping.

        Args:
            flags: Optional dictionary of flag_key -> value.
        """
        self._flags: dict[str, Any] = dict(flags or {})

    def clear(self) -> None:
        """Clear all registered flags."""
        self._flags.clear()

    def get_all_flags(self) -> dict[str, Any]:
        """Return a copy of all registered flags for debugging and UI introspection.

        Returns:
            Dictionary mapping flag keys to their configured values.
        """
        return dict(self._flags)

    def get_boolean_details(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> FlagEvaluationDetails[bool]:
        """Evaluate a boolean feature flag with complete resolution metadata."""
        if flag_key in self._flags:
            val = self._flags[flag_key]
            if isinstance(val, bool):
                return FlagEvaluationDetails(
                    flag_key=flag_key,
                    value=val,
                    reason=FlagEvaluationReason.STATIC,
                )
        return FlagEvaluationDetails(
            flag_key=flag_key,
            value=default,
            reason=FlagEvaluationReason.DEFAULT,
        )

    def get_boolean_value(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag (alias for is_enabled)."""
        return self.is_enabled(flag_key, default=default, context=context)

    def get_float_value(
        self,
        flag_key: str,
        default: float,
        context: EvaluationContext | None = None,
    ) -> float:
        """Evaluate a floating-point feature flag."""
        val = self._flags.get(flag_key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
        return default

    def get_integer_value(
        self,
        flag_key: str,
        default: int,
        context: EvaluationContext | None = None,
    ) -> int:
        """Evaluate an integer feature flag."""
        val = self._flags.get(flag_key)
        if isinstance(val, int) and not isinstance(val, bool):
            return val
        return default

    def get_object_value(
        self,
        flag_key: str,
        default: Mapping[str, Any],
        context: EvaluationContext | None = None,
    ) -> Mapping[str, Any]:
        """Evaluate a structured JSON/dictionary feature flag."""
        val = self._flags.get(flag_key)
        if isinstance(val, Mapping):
            return val
        return default

    def get_string_value(
        self,
        flag_key: str,
        default: str,
        context: EvaluationContext | None = None,
    ) -> str:
        """Evaluate a string feature flag."""
        val = self._flags.get(flag_key)
        if isinstance(val, str):
            return val
        return default

    def is_enabled(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag."""
        val = self._flags.get(flag_key)
        if isinstance(val, bool):
            return val
        return default

    def remove_flag(self, flag_key: str) -> None:
        """Remove a registered flag.

        Args:
            flag_key: Flag identifier.
        """
        self._flags.pop(flag_key, None)

    def set_flag(self, flag_key: str, value: Any) -> None:
        """Set or override a flag value at runtime.

        Args:
            flag_key: Flag identifier.
            value: Flag value (bool, str, int, float, dict).
        """
        self._flags[flag_key] = value


__all__ = [
    "InMemoryFeatureFlagAdapter",
]
