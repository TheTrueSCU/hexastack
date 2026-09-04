import importlib.util
from collections.abc import Mapping
from typing import Any

from hexastack_core.domain.config import HexastackConfig
from hexastack_core.domain.feature_flags import (
    EvaluationContext,
    FlagEvaluationDetails,
    FlagEvaluationReason,
)
from hexastack_core.ports.feature_flags import FeatureFlagPort


class ConfigFeatureFlagAdapter(FeatureFlagPort):
    """Feature flag adapter backed by HexastackConfig and static package inspection.

    Notes/Architectural Intent:
        Evaluates flags against loaded application configuration (`HexastackConfig`),
        environment overrides, and static optional package installation checks
        (via `importlib.util.find_spec`).
    """

    def __init__(
        self,
        config: HexastackConfig | None = None,
        overrides: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize adapter with optional configuration and static overrides.

        Args:
            config: Optional HexastackConfig instance.
            overrides: Optional runtime dictionary overrides.
        """
        self._config = config
        self._overrides: dict[str, Any] = dict(overrides or {})

    def get_all_flags(self) -> dict[str, Any]:
        """Return a dictionary of all active flags and overrides for UI introspection.

        Returns:
            Dictionary mapping flag keys to their configured values.
        """
        flags: dict[str, Any] = dict(self._overrides)
        if self._config is not None and hasattr(self._config, "_core"):
            for attr in dir(self._config._core):
                if not attr.startswith("_"):
                    val = getattr(self._config._core, attr)
                    if isinstance(val, (bool, str, int, float)):
                        flags[f"core.{attr}"] = val
        return flags

    def _lookup_config_path(self, path: str) -> Any:
        """Lookup nested attribute or dictionary key in config."""
        if self._config is None:
            return None

        # Check in _core first if top-level attribute
        if hasattr(self._config, "_core"):
            if hasattr(self._config._core, path):
                return getattr(self._config._core, path)
            if hasattr(self._config, "_sections"):
                parts = path.split(".", 1)
                if len(parts) == 2 and parts[0] in self._config._sections:
                    section = self._config._sections[parts[0]]
                    return getattr(section, parts[1], None)

        parts = path.split(".")
        current: Any = self._config
        for part in parts:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
        return current

    def get_boolean_details(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> FlagEvaluationDetails[bool]:
        """Evaluate boolean flag with resolution reason."""
        if flag_key in self._overrides:
            val = self._overrides[flag_key]
            if isinstance(val, bool):
                return FlagEvaluationDetails(
                    flag_key=flag_key,
                    value=val,
                    reason=FlagEvaluationReason.STATIC,
                )

        if flag_key.startswith("features.lib."):
            lib_name = flag_key.removeprefix("features.lib.")
            found = importlib.util.find_spec(lib_name) is not None
            return FlagEvaluationDetails(
                flag_key=flag_key,
                value=found,
                reason=FlagEvaluationReason.STATIC,
            )

        if self._config is not None:
            val = self._lookup_config_path(flag_key)
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
        """Evaluate a boolean feature flag."""
        return self.is_enabled(flag_key, default=default, context=context)

    def get_float_value(
        self,
        flag_key: str,
        default: float,
        context: EvaluationContext | None = None,
    ) -> float:
        """Evaluate a floating-point feature flag."""
        if flag_key in self._overrides:
            val = self._overrides[flag_key]
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                return float(val)

        if self._config is not None:
            val = self._lookup_config_path(flag_key)
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
        if flag_key in self._overrides:
            val = self._overrides[flag_key]
            if isinstance(val, int) and not isinstance(val, bool):
                return val

        if self._config is not None:
            val = self._lookup_config_path(flag_key)
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
        if flag_key in self._overrides:
            val = self._overrides[flag_key]
            if isinstance(val, Mapping):
                return val

        if self._config is not None:
            val = self._lookup_config_path(flag_key)
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
        if flag_key in self._overrides:
            val = self._overrides[flag_key]
            if isinstance(val, str):
                return val

        if self._config is not None:
            val = self._lookup_config_path(flag_key)
            if isinstance(val, str):
                return val

        return default

    def is_enabled(
        self,
        flag_key: str,
        default: bool = False,
        context: EvaluationContext | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag against overrides, config, and package checks."""
        # 1. Overrides take precedence
        if flag_key in self._overrides:
            val = self._overrides[flag_key]
            if isinstance(val, bool):
                return val

        # 2. Check for dynamic library presence flags (e.g., 'features.lib.<pkg>')
        if flag_key.startswith("features.lib."):
            lib_name = flag_key.removeprefix("features.lib.")
            return importlib.util.find_spec(lib_name) is not None

        # 3. Check loaded configuration dict if available
        if self._config is not None:
            # Match top-level or dotted section attributes
            val = self._lookup_config_path(flag_key)
            if isinstance(val, bool):
                return val

        return default


__all__ = [
    "ConfigFeatureFlagAdapter",
]
