"""Unit tests for OpenFeature provider factory initialization and error handling."""

from __future__ import annotations

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_flags.adapters.providers.factory import initialize_openfeature_provider
from hexastack_flags.domain.models import (
    FeatureFlagProviderType,
    FlagProviderOptions,
)


@pytest.fixture(autouse=True)
def _reset_openfeature_provider():
    """Ensure OpenFeature default provider is reset to in-memory after each test."""
    yield
    from openfeature import api
    from openfeature.provider.in_memory_provider import InMemoryProvider

    api.set_provider(InMemoryProvider({}))


def test_initialize_in_memory_provider():
    """Verify in-memory provider initialization with custom flag dictionary."""
    from hexastack_flags.adapters.openfeature import OpenFeatureFlagAdapter

    initialize_openfeature_provider(
        provider_type=FeatureFlagProviderType.IN_MEMORY,
        in_memory_flags={"feature_x": True, "feature_off": False, "count": 10},
    )
    adapter = OpenFeatureFlagAdapter()
    assert adapter.is_enabled("feature_x") is True
    assert adapter.is_enabled("feature_off") is False


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
    # Also verify default options resolution when options is None
    initialize_openfeature_provider(
        provider_type=FeatureFlagProviderType.FLAGD,
        options=None,
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


def test_initialize_env_provider(monkeypatch: pytest.MonkeyPatch):
    """Verify ENV provider parses environment variables with prefix."""
    from hexastack_flags.adapters.openfeature import OpenFeatureFlagAdapter

    monkeypatch.setenv("FEATURE_FLAG_BETA_MODE", "true")
    monkeypatch.setenv("FEATURE_FLAG_MAX_RETRIES", "7")
    monkeypatch.setenv("FEATURE_FLAG_ZERO_FLAG", "0")
    monkeypatch.setenv("FEATURE_FLAG_ONE_FLAG", "1")
    monkeypatch.setenv("FEATURE_FLAG_PAYLOAD", '{"nested": "data"}')

    initialize_openfeature_provider(
        provider_type=FeatureFlagProviderType.ENV,
    )
    adapter = OpenFeatureFlagAdapter()
    beta_enabled = adapter.is_enabled("beta_mode")
    assert beta_enabled is True

    retries = adapter.get_integer_value("max_retries")
    assert retries == 7

    zero_val = adapter.get_integer_value("zero_flag")
    assert zero_val == 0

    one_val = adapter.get_integer_value("one_flag")
    assert one_val == 1

    payload = adapter.get_object_value("payload")
    assert payload == {"nested": "data"}


def test_parse_env_flag_value_deep_recursion():
    """Verify deeply nested JSON raising RecursionError falls back to raw string."""
    from unittest.mock import patch

    from hexastack_flags.adapters.providers.factory import _parse_env_flag_value

    with patch(
        "json.loads", side_effect=RecursionError("maximum recursion depth exceeded")
    ):
        res = _parse_env_flag_value('{"deep": true}')
        assert res == '{"deep": true}'
