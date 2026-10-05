from typing import Any

import pytest

from hexastack_core.domain import Generic
from hexastack_core.ports.presenter import PresenterPort
from hexastack_cqrs.infra.registries.presenter import (
    PresenterRegistry,
    PresenterRegistryError,
)


class SampleDTO(Generic):
    name: str


class JsonPresenter(PresenterPort):
    def present(self, instance: Generic) -> Any | None:
        if isinstance(instance, SampleDTO):
            return {"name": instance.name, "format": "json"}
        return None


def test_presenter_registry():
    registry = PresenterRegistry()
    presenter = JsonPresenter()
    registry.register(SampleDTO, "json", presenter)

    assert registry.get(SampleDTO, "json") == presenter

    presented = registry.present(SampleDTO(name="Alice"), "json")
    assert presented == {"name": "Alice", "format": "json"}


def test_presenter_registry_all_clear_contains():
    registry = PresenterRegistry()
    presenter = JsonPresenter()
    registry.register(SampleDTO, "json", presenter)

    assert (SampleDTO, "json") in registry
    assert (SampleDTO, "xml") not in registry
    assert len(registry.all) == 1

    registry.clear()
    assert len(registry.all) == 0
    assert (SampleDTO, "json") not in registry


def test_presenter_registry_unregistered_raises():
    registry = PresenterRegistry()

    # Explicit reraise=True
    with pytest.raises(PresenterRegistryError) as exc_info:
        registry.present(SampleDTO(name="Bob"), "xml", reraise=True)
    assert str(exc_info.value) == "No Presenter registered for SampleDTO as xml."

    # Default reraise=True
    with pytest.raises(PresenterRegistryError) as exc_default:
        registry.present(SampleDTO(name="Bob"), "html")
    assert str(exc_default.value) == "No Presenter registered for SampleDTO as html."


def test_presenter_registry_unregistered_returns_none_when_reraise_false():
    registry = PresenterRegistry()
    assert registry.present(SampleDTO(name="Bob"), "xml", reraise=False) is None
