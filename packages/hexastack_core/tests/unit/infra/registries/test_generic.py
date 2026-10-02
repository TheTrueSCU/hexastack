import pytest

from hexastack_core.domain import Command
from hexastack_core.infra import (
    GenericHandlerRegistry,
    GenericHandlerRegistryError,
    GenericTypeRegistry,
    GenericTypeRegistryError,
)


class _SampleCommand(Command):
    name: str


class _SubCommand(_SampleCommand):
    pass


class _UnregisteredCommand(Command):
    pass


def test_handler_registry_all_clear_contains():
    registry = GenericHandlerRegistry[Command, str]()
    registry.register(_SampleCommand, lambda cmd: "ok")

    assert _SampleCommand in registry
    assert _UnregisteredCommand not in registry
    assert len(registry.all) == 1

    registry.clear()
    assert len(registry.all) == 0
    assert _SampleCommand not in registry


def test_handler_registry_dispatches_registered_handler():
    registry = GenericHandlerRegistry[Command, str]()

    def handler(cmd: _SampleCommand) -> str:
        return f"Handled {cmd.name}"

    registry.register(_SampleCommand, handler)
    assert registry.handle(_SampleCommand(name="hello")) == "Handled hello"


def test_handler_registry_raises_on_unregistered():
    registry = GenericHandlerRegistry[Command, str]()

    with pytest.raises(GenericHandlerRegistryError) as exc_info:
        registry.handle(_UnregisteredCommand(), reraise=True)

    assert "No handler registered for '_UnregisteredCommand'" in str(exc_info.value)


def test_handler_registry_returns_none_when_reraise_false():
    registry = GenericHandlerRegistry[Command, str]()
    assert registry.handle(_UnregisteredCommand(), reraise=False) is None


def test_handler_registry_subclass_fallback():
    registry = GenericHandlerRegistry[Command, str]()
    registry.register(_SampleCommand, lambda cmd: f"Handled {cmd.name}")

    assert registry.handle(_SubCommand(name="sub")) == "Handled sub"
    assert registry.get(_SubCommand, exact=True) is None
    assert registry.get(_SubCommand, exact=False) is not None


def test_type_registry_all_returns_copy():
    registry = GenericTypeRegistry[Command]()
    registry.register(_SampleCommand)
    snapshot = registry.all
    snapshot["injected"] = _UnregisteredCommand  # type: ignore[assignment]
    # original registry should be unaffected
    assert "injected" not in registry.all


def test_type_registry_contains_and_clear():
    registry = GenericTypeRegistry[Command]()
    registry.register(_SampleCommand)

    assert "_SampleCommand" in registry
    assert "Unknown" not in registry

    registry.clear()
    assert "_SampleCommand" not in registry
    assert len(registry.all) == 0


def test_type_registry_get_registered():
    registry = GenericTypeRegistry[Command]()
    registry.register(_SampleCommand)
    assert registry.get("_SampleCommand") == _SampleCommand


def test_type_registry_raises_on_unregistered():
    registry = GenericTypeRegistry[Command]()

    with pytest.raises(GenericTypeRegistryError) as exc_info:
        registry.get("UnknownCommand")

    assert "Type 'UnknownCommand' is not registered." in str(exc_info.value)


def test_type_registry_register_by_name():
    registry = GenericTypeRegistry[Command]()
    registry.register_by_name(_SampleCommand, "alias")
    assert registry.get("alias") == _SampleCommand
