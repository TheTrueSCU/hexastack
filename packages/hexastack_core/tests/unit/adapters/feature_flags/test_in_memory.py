from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.domain.feature_flags import FlagEvaluationReason


def test_in_memory_feature_flag_adapter_boolean():
    adapter = InMemoryFeatureFlagAdapter({"feature.search": True, "feature.v2": False})

    assert adapter.is_enabled("feature.search") is True
    assert adapter.is_enabled("feature.v2") is False
    assert adapter.is_enabled("feature.nonexistent", default=True) is True
    assert adapter.is_enabled("feature.nonexistent", default=False) is False

    # Details
    details_found = adapter.get_boolean_details("feature.search")
    assert details_found.value is True
    assert details_found.reason == FlagEvaluationReason.STATIC

    details_missing = adapter.get_boolean_details("feature.missing", default=False)
    assert details_missing.value is False
    assert details_missing.reason == FlagEvaluationReason.DEFAULT


def test_in_memory_feature_flag_adapter_types():
    adapter = InMemoryFeatureFlagAdapter(
        {
            "flag.str": "variation_a",
            "flag.int": 42,
            "flag.float": 3.14,
            "flag.obj": {"k": "v"},
        }
    )

    # String
    assert adapter.get_string_value("flag.str", default="def") == "variation_a"
    assert adapter.get_string_value("flag.missing", default="def") == "def"

    # Integer
    assert adapter.get_integer_value("flag.int", default=0) == 42
    assert adapter.get_integer_value("flag.missing", default=10) == 10

    # Float
    assert adapter.get_float_value("flag.float", default=0.0) == 3.14
    assert adapter.get_float_value("flag.int", default=0.0) == 42.0
    assert adapter.get_float_value("flag.missing", default=1.5) == 1.5

    # Object
    assert adapter.get_object_value("flag.obj", default={}) == {"k": "v"}
    assert adapter.get_object_value("flag.missing", default={"x": 1}) == {"x": 1}


def test_in_memory_feature_flag_mutation():
    adapter = InMemoryFeatureFlagAdapter()
    assert adapter.is_enabled("beta") is False

    adapter.set_flag("beta", True)
    assert adapter.is_enabled("beta") is True

    adapter.remove_flag("beta")
    assert adapter.is_enabled("beta") is False

    adapter.set_flag("beta", True)
    adapter.clear()
    assert adapter.is_enabled("beta") is False


def test_in_memory_feature_flag_get_all_flags_and_clear():
    """Verify get_all_flags returns dictionary copy of flags and clear resets adapter."""
    adapter = InMemoryFeatureFlagAdapter({"flag.one": True, "flag.two": False})
    all_flags = adapter.get_all_flags()
    assert all_flags == {"flag.one": True, "flag.two": False}

    adapter.clear()
    assert adapter.get_all_flags() == {}
