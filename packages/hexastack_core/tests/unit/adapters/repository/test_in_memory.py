from collections.abc import Callable
from typing import Any

import pytest
from hexastack_core.adapters.repository import InMemoryRepository


class DummyEntity:
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class CustomKeyEntity:
    def __init__(self, key: int, name: str) -> None:
        self.key = key
        self.name = name


def test_in_memory_repository_default_id_attribute(
    in_memory_repo: InMemoryRepository[DummyEntity, str],
):
    entity = DummyEntity(id="e1", name="Alice")
    in_memory_repo.add(entity)

    assert in_memory_repo.get_by_id("e1") == entity
    assert in_memory_repo.get_by_id("missing") is None
    assert in_memory_repo.all() == [entity]

    in_memory_repo.remove("e1")
    assert in_memory_repo.get_by_id("e1") is None
    assert in_memory_repo.all() == []


def test_in_memory_repository_custom_id_attr(
    in_memory_repo_factory: Callable[..., InMemoryRepository[Any, Any]],
):
    repo = in_memory_repo_factory(id_attr="key")
    entity = CustomKeyEntity(key=101, name="Bob")
    repo.add(entity)

    assert repo.get_by_id(101) == entity
    assert repo.all() == [entity]


def test_in_memory_repository_custom_id_getter(
    in_memory_repo_factory: Callable[..., InMemoryRepository[Any, Any]],
):
    repo = in_memory_repo_factory(id_getter=lambda e: e.key)
    entity = CustomKeyEntity(key=202, name="Charlie")
    repo.add(entity)

    assert repo.get_by_id(202) == entity
    assert repo.all() == [entity]


def test_in_memory_repository_clear(
    in_memory_repo: InMemoryRepository[DummyEntity, str],
):
    in_memory_repo.add(DummyEntity(id="1", name="One"))
    in_memory_repo.add(DummyEntity(id="2", name="Two"))

    assert len(in_memory_repo.all()) == 2
    in_memory_repo.clear()
    assert len(in_memory_repo.all()) == 0


def test_in_memory_repository_missing_id_raises_attribute_error(
    in_memory_repo: InMemoryRepository[CustomKeyEntity, str],
):
    with pytest.raises(AttributeError):
        in_memory_repo.add(CustomKeyEntity(key=1, name="Error"))
