from dataclasses import dataclass

import pytest

from hexastack_core.adapters.repository import AsyncInMemoryRepository


@dataclass
class User:
    id: str
    name: str


@pytest.mark.anyio
async def test_async_in_memory_repository():
    repo = AsyncInMemoryRepository[User, str]()

    u1 = User(id="u1", name="Alice")
    u2 = User(id="u2", name="Bob")

    await repo.add_async(u1)
    await repo.add_async(u2)

    assert await repo.get_by_id_async("u1") == u1
    assert await repo.get_by_id_async("unknown") is None

    all_users = await repo.all_async()
    assert len(all_users) == 2
    assert u1 in all_users
    assert u2 in all_users

    await repo.remove_async("u1")
    assert await repo.get_by_id_async("u1") is None
    assert len(await repo.all_async()) == 1

    repo.clear()
    assert len(await repo.all_async()) == 0
