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


def test_initialize_unleash_and_flipt_mocked():
    """Verify Unleash and Flipt provider initialization when modules are present."""
    from unittest.mock import MagicMock, patch

    mock_unleash_cls = MagicMock()
    mock_flipt_cls = MagicMock()

    with (
        patch("importlib.import_module") as mock_import,
    ):

        def _mock_import(name):
            if "unleash" in name:
                m = MagicMock()
                m.UnleashProvider = mock_unleash_cls
                return m
            if "flipt" in name:
                m = MagicMock()
                m.FliptProvider = mock_flipt_cls
                return m
            raise ImportError(name)

        mock_import.side_effect = _mock_import

        opts_unleash = FlagProviderOptions(
            host="localhost",
            port=4242,
            extra={"api_token": "secret"},  # pragma: allowlist secret
        )
        initialize_openfeature_provider(
            FeatureFlagProviderType.UNLEASH, options=opts_unleash
        )
        mock_unleash_cls.assert_called_once()

        opts_flipt = FlagProviderOptions(host="localhost", port=9000)
        initialize_openfeature_provider(
            FeatureFlagProviderType.FLIPT, options=opts_flipt
        )
        mock_flipt_cls.assert_called_once()
