"""Unit tests for feature flags ports."""

from hexastack_core.ports.feature_flags import FeatureFlagPort


def test_feature_flag_port_interface() -> None:
    assert hasattr(FeatureFlagPort, "is_enabled")


def test_feature_flag_port_protocol_default_callables() -> None:
    """Verify protocol definition methods can be called directly or checked on dummy implementation."""
    from typing import Any

    dummy: Any = None
    FeatureFlagPort.get_boolean_details(dummy, "flag")
    FeatureFlagPort.get_boolean_value(dummy, "flag")
    FeatureFlagPort.get_float_value(dummy, "flag", 1.0)
    FeatureFlagPort.get_integer_value(dummy, "flag", 1)
    FeatureFlagPort.get_object_value(dummy, "flag", {})
    FeatureFlagPort.get_string_value(dummy, "flag", "default")
    FeatureFlagPort.is_enabled(dummy, "flag")
