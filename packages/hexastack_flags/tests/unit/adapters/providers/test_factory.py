"""Unit tests for OpenFeature provider factory initialization and error handling."""

from __future__ import annotations

import pytest
from hexastack_flags.adapters.providers.factory import initialize_openfeature_provider
from hexastack_flags.domain.models import (
    FeatureFlagProviderType,
    FlagProviderOptions,
)

from hexastack_core.domain.exceptions import MissingDependencyError


def test_initialize_in_memory_provider():
    """Verify in-memory provider initialization with custom flag dictionary."""
    initialize_openfeature_provider(
        provider_type=FeatureFlagProviderType.IN_MEMORY,
        in_memory_flags={"feature_x": True, "count": 10},
    )


def test_initialize_unleash_missing_dependency():
    """Verify missing dependency error raised with actionable installation prompt."""
    with pytest.raises(MissingDependencyError) as exc_info:
        initialize_openfeature_provider(
            provider_type=FeatureFlagProviderType.UNLEASH,
            options=FlagProviderOptions(host="localhost", port=4242),
        )
    assert "openfeature-provider-unleash" in str(exc_info.value)
    assert "hexastack-flags[unleash]" in str(exc_info.value)


def test_initialize_flipt_missing_dependency():
    """Verify missing dependency error raised with actionable installation prompt."""
    with pytest.raises(MissingDependencyError) as exc_info:
        initialize_openfeature_provider(
            provider_type=FeatureFlagProviderType.FLIPT,
            options=FlagProviderOptions(host="localhost", port=9000),
        )
    assert "openfeature-provider-flipt" in str(exc_info.value)
    assert "hexastack-flags[flipt]" in str(exc_info.value)


def test_initialize_flagd_provider():
    """Verify Flagd provider initialization with options."""
    initialize_openfeature_provider(
        provider_type=FeatureFlagProviderType.FLAGD,
        options=FlagProviderOptions(host="localhost", port=8013, timeout_ms=3000),
    )
