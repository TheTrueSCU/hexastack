import importlib.util
from typing import Any

import pytest

from hexastack_core.adapters.feature_flags.config import ConfigFeatureFlagAdapter
from hexastack_core.ports.feature_flags import FeatureFlagPort


def require_extra(package_name: str, reason: str | None = None) -> Any:
    """Pytest decorator to skip a test if an optional package/extra is not installed.

    Notes/Architectural Intent:
        Uses static module spec discovery (`importlib.util.find_spec`) to conditionally
        skip tests requiring optional extras (e.g. `redis`, `opentelemetry`, `strawberry`).

    Args:
        package_name: The Python import package name to verify (e.g. 'redis', 'loguru').
        reason: Optional custom skip explanation message.

    Returns:
        Pytest skipif mark decorator.
    """
    is_installed = importlib.util.find_spec(package_name) is not None
    msg = reason or f"Optional extra '{package_name}' is not installed."
    return pytest.mark.skipif(not is_installed, reason=msg)


def require_feature(
    flag_key: str,
    default: bool = False,
    flags: FeatureFlagPort | None = None,
    reason: str | None = None,
) -> Any:
    """Pytest decorator to skip a test if a specific feature flag is disabled.

    Notes/Architectural Intent:
        Evaluates the requested feature flag against the supplied `FeatureFlagPort`
        (or default `ConfigFeatureFlagAdapter`), skipping the test if evaluated to False.

    Args:
        flag_key: Unique identifier of the feature flag to check.
        default: Fallback boolean value if flag is not explicitly configured.
        flags: Optional explicit FeatureFlagPort adapter instance.
        reason: Optional custom skip explanation message.

    Returns:
        Pytest skipif mark decorator.
    """
    adapter = flags or ConfigFeatureFlagAdapter()
    is_enabled = adapter.is_enabled(flag_key, default=default)
    msg = reason or f"Feature flag '{flag_key}' is disabled."
    return pytest.mark.skipif(not is_enabled, reason=msg)


__all__ = [
    "require_extra",
    "require_feature",
]
