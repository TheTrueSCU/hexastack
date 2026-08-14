import pytest

from hexastack_core.domain import Command
from hexastack_cqrs.infra.registries import HandlerRegistry, HandlerRegistryError


class _DummyCommand(Command):
    val: int


def test_register_and_handle():
    reg = HandlerRegistry()
    reg.register(_DummyCommand, lambda cmd: cmd.val * 2)
    assert reg.handle(_DummyCommand(val=21)) == 42


def test_handle_unregistered_raises():
    reg = HandlerRegistry()
    with pytest.raises(HandlerRegistryError):
        reg.handle(_DummyCommand(val=0), reraise=True)


def test_handle_unregistered_returns_none_when_reraise_false():
    reg = HandlerRegistry()
    assert reg.handle(_DummyCommand(val=0), reraise=False) is None
