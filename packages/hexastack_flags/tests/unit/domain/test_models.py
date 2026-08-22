"""Unit tests for flags domain models."""

from hexastack_flags.domain.models import FeatureFlagProviderType, FlagProviderOptions


def test_flags_models() -> None:
    assert FeatureFlagProviderType.IN_MEMORY == "in_memory"
    assert FeatureFlagProviderType.FLAGD == "flagd"
    options = FlagProviderOptions(host="localhost", port=8013)
    assert options.host == "localhost"
    assert options.port == 8013
