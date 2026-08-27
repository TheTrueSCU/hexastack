from hexastack_flags.adapters.openfeature import OpenFeatureFlagAdapter
from hexastack_flags.adapters.providers.factory import initialize_openfeature_provider
from hexastack_flags.domain.models import FeatureFlagProviderType

from hexastack_core.domain.feature_flags import EvaluationContext


def test_openfeature_adapter_in_memory():
    initialize_openfeature_provider(
        provider_type=FeatureFlagProviderType.IN_MEMORY,
        in_memory_flags={
            "bool_flag": True,
            "string_flag": "dark_mode",
            "int_flag": 42,
            "float_flag": 3.14,
            "json_flag": {"key": "val"},
        },
    )

    adapter = OpenFeatureFlagAdapter()

    # 1. Boolean
    assert adapter.is_enabled("bool_flag", default=False) is True
    assert adapter.get_boolean_value("bool_flag", default=False) is True
    assert adapter.is_enabled("missing_flag", default=False) is False

    # 2. String
    assert adapter.get_string_value("string_flag", default="light") == "dark_mode"
    assert adapter.get_string_value("missing_str", default="fallback") == "fallback"

    # 3. Int & Float
    assert adapter.get_integer_value("int_flag", default=0) == 42
    assert adapter.get_float_value("float_flag", default=0.0) == 3.14

    # 4. JSON Object
    assert adapter.get_object_value("json_flag", default={}) == {"key": "val"}

    # 5. Details & Reason Mapping
    ctx = EvaluationContext(
        user_id="u-123",
        tenant_id="tenant-alpha",
        targeting_key="target-override",
        roles=frozenset({"admin", "beta_tester"}),
        attributes={"country": "US"},
    )
    details = adapter.get_boolean_details("bool_flag", default=False, context=ctx)
    assert details.flag_key == "bool_flag"
    assert details.value is True
    assert details.variant == "on"

    # 6. Introspection / get_all_flags
    all_flags = adapter.get_all_flags()
    assert "bool_flag" in all_flags
    assert "string_flag" in all_flags
    assert all_flags["int_flag"] == 42
    assert all_flags["float_flag"] == 3.14

    # 7. Non-dict fallback in get_object_value
    assert adapter.get_object_value("missing_obj", default={"k": "default"}) == {
        "k": "default"
    }


def test_openfeature_factory_missing_dependencies():
    from unittest.mock import patch

    import pytest
    from hexastack_flags.adapters.providers.factory import (
        _build_flagd_provider,
        _build_flipt_provider,
        _build_unleash_provider,
    )
    from hexastack_flags.domain.models import FlagProviderOptions

    from hexastack_core.domain.exceptions import MissingDependencyError

    opts = FlagProviderOptions(host="127.0.0.1", port=8080)
    with patch("importlib.import_module", side_effect=ImportError("No module")):
        with pytest.raises(MissingDependencyError, match="openfeature-provider-flagd"):
            _build_flagd_provider(opts)

        with pytest.raises(MissingDependencyError, match="openfeature-provider-unleash"):
            _build_unleash_provider(opts)

        with pytest.raises(MissingDependencyError, match="openfeature-provider-flipt"):
            _build_flipt_provider(opts)

