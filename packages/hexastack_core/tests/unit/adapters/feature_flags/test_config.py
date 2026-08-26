from typing import Any

from pydantic import BaseModel

from hexastack_core.adapters.feature_flags.config import ConfigFeatureFlagAdapter
from hexastack_core.domain.feature_flags import FlagEvaluationReason
from hexastack_core.infra.config import HexastackConfig


def test_config_feature_flag_adapter_config_inspection():
    from hexastack_core.infra.config import HexastackCoreConfig

    core_cfg = HexastackCoreConfig(
        app_name="TestApp",
        environment="testing",
        debug=True,
    )

    class CustomSection(BaseModel):
        enabled: bool = True
        threshold: int = 42
        ratio: float = 3.14
        settings: dict[str, Any] = {"k": "v"}
        name: str = "section_name"

    config = HexastackConfig(core=core_cfg, sections={"custom": CustomSection()})
    adapter = ConfigFeatureFlagAdapter(config=config)

    assert adapter.is_enabled("debug") is True
    assert adapter.get_string_value("app_name", default="") == "TestApp"
    assert adapter.get_string_value("environment", default="") == "testing"
    assert adapter.is_enabled("nonexistent_prop", default=False) is False
    assert adapter.is_enabled("custom.enabled") is True
    assert adapter.get_integer_value("custom.threshold", default=0) == 42
    assert adapter.get_float_value("custom.ratio", default=0.0) == 3.14
    assert adapter.get_object_value("custom.settings", default={}) == {"k": "v"}
    assert adapter.get_string_value("custom.name", default="") == "section_name"

    details = adapter.get_boolean_details("custom.enabled")
    assert details.value is True
    assert details.reason == FlagEvaluationReason.STATIC

    details_default = adapter.get_boolean_details("custom.missing", default=False)
    assert details_default.value is False
    assert details_default.reason == FlagEvaluationReason.DEFAULT

    all_flags = adapter.get_all_flags()
    assert "core.app_name" in all_flags
    assert all_flags["core.app_name"] == "TestApp"


def test_config_feature_flag_adapter_library_inspection():
    adapter = ConfigFeatureFlagAdapter()

    # Built-in or installed packages
    assert adapter.is_enabled("features.lib.pydantic") is True
    details_found = adapter.get_boolean_details("features.lib.pydantic")
    assert details_found.value is True
    assert details_found.reason == FlagEvaluationReason.STATIC

    # Non-existent package
    assert adapter.is_enabled("features.lib.non_existent_fake_package_xyz") is False
    details_missing = adapter.get_boolean_details(
        "features.lib.non_existent_fake_package_xyz"
    )
    assert details_missing.value is False
    assert details_missing.reason == FlagEvaluationReason.STATIC


def test_config_feature_flag_adapter_overrides():
    adapter = ConfigFeatureFlagAdapter(
        overrides={
            "flag.bool": True,
            "flag.str": "override_val",
            "flag.int": 100,
            "flag.float": 99.9,
            "flag.obj": {"a": 1},
        }
    )

    assert adapter.is_enabled("flag.bool") is True
    assert adapter.get_boolean_value("flag.bool") is True
    assert adapter.get_string_value("flag.str", default="") == "override_val"
    assert adapter.get_integer_value("flag.int", default=0) == 100
    assert adapter.get_float_value("flag.float", default=0.0) == 99.9
    assert adapter.get_object_value("flag.obj", default={}) == {"a": 1}

    details = adapter.get_boolean_details("flag.bool")
    assert details.value is True
    assert details.reason == FlagEvaluationReason.STATIC

    all_flags = adapter.get_all_flags()
    assert all_flags["flag.bool"] is True
    assert all_flags["flag.str"] == "override_val"
