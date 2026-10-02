from hexastack_core.adapters.repository import InMemoryRepository
from hexastack_core.ports.repository import RepositoryPort


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
