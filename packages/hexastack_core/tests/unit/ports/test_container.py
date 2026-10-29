from __future__ import annotations

import rodi

from hexastack_core.infra.container import MicroContainer, create_container
from hexastack_core.ports.container import ContainerPort


class DummyService:
    def __init__(self) -> None:
        self.active = True


def test_micro_container_satisfies_container_port():
    micro = MicroContainer()
    is_proto = isinstance(micro, ContainerPort)
    assert is_proto is True

    chained = micro.add_instance(DummyService())
    assert chained is micro

    has_service = DummyService in micro
    assert has_service is True

    resolved = micro.resolve(DummyService)
    assert isinstance(resolved, DummyService)


def test_rodi_container_satisfies_container_port():
    rodi_c = rodi.Container()
    is_proto = isinstance(rodi_c, ContainerPort)
    assert is_proto is True

    rodi_c.add_instance(DummyService())
    has_service = DummyService in rodi_c
    assert has_service is True

    provider = rodi_c.build_provider()
    resolved = provider.get(DummyService)
    assert isinstance(resolved, DummyService)


def test_create_container_factory():
    container = create_container()
    is_proto = isinstance(container, ContainerPort)
    assert is_proto is True
