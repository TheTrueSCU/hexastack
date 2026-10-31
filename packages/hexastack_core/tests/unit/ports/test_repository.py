import inspect

import pytest

from hexastack_core.adapters.repository import InMemoryRepository
from hexastack_core.ports.repository import AsyncRepositoryPort, RepositoryPort


class UserEntity:
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


def test_repository_port_contract(
    in_memory_repo: InMemoryRepository[UserEntity, str],
):
    # Verify InMemoryRepository satisfies RepositoryPort interface
    repo: RepositoryPort[UserEntity, str] = in_memory_repo
    user = UserEntity(id="u1", name="Alice")

    repo.add(user)
    assert repo.get_by_id("u1") == user
    assert repo.get_by_id("u2") is None

    repo.remove("u1")
    assert repo.get_by_id("u1") is None


def test_repository_port_is_abstract() -> None:
    """Verify that RepositoryPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(RepositoryPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        RepositoryPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_repository_port_abstract_methods() -> None:
    """Verify abstract methods on RepositoryPort."""
    expected = {"add", "get_by_id", "remove"}
    abstracts = RepositoryPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_repository_port_is_abstract() -> None:
    """Verify that AsyncRepositoryPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncRepositoryPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncRepositoryPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_repository_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncRepositoryPort."""
    expected = {"add_async", "get_by_id_async", "remove_async"}
    abstracts = AsyncRepositoryPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
