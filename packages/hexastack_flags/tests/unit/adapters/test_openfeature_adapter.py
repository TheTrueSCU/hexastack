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

    # 5. Details
    ctx = EvaluationContext(user_id="u-123", tenant_id="tenant-alpha")
    details = adapter.get_boolean_details("bool_flag", default=False, context=ctx)
    assert details.flag_key == "bool_flag"
    assert details.value is True
