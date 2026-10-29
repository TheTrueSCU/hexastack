from __future__ import annotations

import abc

import pytest

from hexastack_core.infra.container import (
    CannotResolveException,
    ContainerException,
    MicroContainer,
)


class BaseService(abc.ABC):
    @abc.abstractmethod
    def work(self) -> str:
        """Abstract work method."""


class ConcreteService(BaseService):
    def work(self) -> str:
        return "done"


class DependentService:
    def __init__(self, service: BaseService) -> None:
        self.service = service


class ParameterlessService:
    def __init__(self) -> None:
        self.value = 42


class UnresolvableService:
    def __init__(self, missing_arg: int) -> None:
        self.missing_arg = missing_arg


def test_micro_container_add_instance():
    container = MicroContainer()
    instance = ConcreteService()

    chained = container.add_instance(instance, declared_class=BaseService)
    assert chained is container

    has_base = BaseService in container
    assert has_base is True

    has_concrete = ConcreteService in container
    assert has_concrete is True

    has_named = "BaseService" in container
    assert has_named is True

    resolved_base = container.resolve(BaseService)
    assert resolved_base is instance

    resolved_concrete = container.resolve(ConcreteService)
    assert resolved_concrete is instance

    resolved_get = container.get(BaseService)
    assert resolved_get is instance


def test_micro_container_add_singleton():
    container = MicroContainer()
    counter = 0

    def factory() -> ParameterlessService:
        nonlocal counter
        counter += 1
        return ParameterlessService()

    chained = container.add_singleton(ParameterlessService, factory)
    assert chained is container

    first = container.resolve(ParameterlessService)
    second = container.resolve(ParameterlessService)

    assert first is second
    assert counter == 1


def test_micro_container_add_transient():
    container = MicroContainer()
    counter = 0

    def factory() -> ParameterlessService:
        nonlocal counter
        counter += 1
        return ParameterlessService()

    chained = container.add_transient(ParameterlessService, factory)
    assert chained is container

    first = container.resolve(ParameterlessService)
    second = container.resolve(ParameterlessService)

    assert first is not second
    assert counter == 2


def test_micro_container_add_scoped():
    container = MicroContainer()
    container.add_scoped(ParameterlessService)

    first = container.resolve(ParameterlessService)
    second = container.resolve(ParameterlessService)

    assert first is second


def test_micro_container_factory_with_container():
    container = MicroContainer()
    container.add_instance(ConcreteService(), declared_class=BaseService)

    def dependent_factory(c: MicroContainer) -> DependentService:
        svc = c.resolve(BaseService)
        return DependentService(service=svc)

    container.add_singleton(DependentService, dependent_factory)

    resolved = container.resolve(DependentService)
    work_res = resolved.service.work()
    assert work_res == "done"


def test_micro_container_reflection_resolution():
    container = MicroContainer()
    container.add_instance(ConcreteService(), declared_class=BaseService)

    # Auto-resolve DependentService via constructor parameter inspect.signature
    dependent = container.resolve(DependentService)
    work_res = dependent.service.work()
    assert work_res == "done"

    # Parameterless class
    paramless = container.resolve(ParameterlessService)
    assert paramless.value == 42


def test_micro_container_register_protocol():
    container = MicroContainer()

    # Register with callable factory
    container.register(ParameterlessService, lambda: ParameterlessService())
    has_reg = ParameterlessService in container
    assert has_reg is True
    first = container.resolve(ParameterlessService)
    assert isinstance(first, ParameterlessService)

    # Register with type directly
    container.register(ConcreteService)
    has_concrete = ConcreteService in container
    assert has_concrete is True


def test_micro_container_build_provider():
    container = MicroContainer()
    provider = container.build_provider()
    assert provider is container


def test_micro_container_cannot_resolve_abstract():
    container = MicroContainer()

    with pytest.raises(CannotResolveException) as exc_info:
        container.resolve(BaseService)

    err_msg = str(exc_info.value)
    assert "BaseService" in err_msg
    assert isinstance(exc_info.value, ContainerException)


def test_micro_container_cannot_resolve_missing_unregistered():
    container = MicroContainer()

    with pytest.raises(CannotResolveException) as exc_info:
        container.resolve("NonExistentService")

    err_msg = str(exc_info.value)
    assert "NonExistentService" in err_msg


def test_micro_container_contains_false():
    container = MicroContainer()
    has_unknown = "UnknownKey" in container
    assert has_unknown is False
