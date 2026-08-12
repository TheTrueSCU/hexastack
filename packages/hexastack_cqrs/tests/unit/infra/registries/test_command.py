import pytest
from hexastack_core.domain import Command
from hexastack_cqrs.infra.registries import CommandRegistry, CommandRegistryError


class _DummyCommand(Command):
    val: int


def test_register_and_get():
    reg = CommandRegistry()
    reg.register(_DummyCommand)
    assert reg.get("_DummyCommand") == _DummyCommand


def test_get_unregistered_raises():
    reg = CommandRegistry()
    with pytest.raises(CommandRegistryError):
        reg.get("NonExistent")
