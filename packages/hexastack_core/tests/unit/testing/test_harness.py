"""Unit tests for Hexastack core testing utilities."""

from dataclasses import dataclass

from hypothesis import given
from pydantic import BaseModel

from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.domain import Command
from hexastack_core.testing import (
    TestRuntime,
    cqrs_strategy,
    create_test_runtime,
    flag_scope,
    get_layer_restrictions,
    parametrize_flags,
)


@dataclass(frozen=True)
class SampleCommand(Command):
    user_id: str
    age: int


class SampleModel(BaseModel):
    name: str
    is_active: bool


@given(cmd=cqrs_strategy(SampleCommand))
def test_cqrs_strategy_fuzz(cmd: SampleCommand):
    assert isinstance(cmd, SampleCommand)
    assert isinstance(cmd.user_id, str)
    assert isinstance(cmd.age, int)


def test_create_test_runtime():
    runtime = create_test_runtime(
        flag_overrides={"beta_test": True},
        instances={str: "hello_service"},
    )
    assert isinstance(runtime, TestRuntime)
    assert runtime.flags.is_enabled("beta_test") is True
    assert runtime.resolve(str) == "hello_service"


def test_flag_scope():
    flags = InMemoryFeatureFlagAdapter({"my_flag": False})
    assert flags.is_enabled("my_flag") is False

    with flag_scope(flags, {"my_flag": True}):
        assert flags.is_enabled("my_flag") is True

    # Restores original state
    assert flags.is_enabled("my_flag") is False


def test_layer_restrictions():
    restrictions = get_layer_restrictions()
    assert "domain" in restrictions
    assert "ports" in restrictions
    assert "adapters" in restrictions
    assert "infra" in restrictions


@parametrize_flags("test.flag", [True, False])
def test_parametrize_flags(flag__test_flag: bool):
    assert isinstance(flag__test_flag, bool)
