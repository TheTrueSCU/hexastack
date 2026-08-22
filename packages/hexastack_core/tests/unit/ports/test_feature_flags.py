"""Unit tests for feature flags ports."""

from hexastack_core.ports.feature_flags import FeatureFlagPort


def test_feature_flag_port_interface() -> None:
    assert hasattr(FeatureFlagPort, "is_enabled")
