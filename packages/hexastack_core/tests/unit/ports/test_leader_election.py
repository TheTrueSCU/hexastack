import pytest

from hexastack_core.ports.leader_election import (
    AsyncLeaderElectionPort,
    LeaderElectionPort,
)


class DummyLeaderElection(LeaderElectionPort):
    def is_leader(self) -> bool:
        return False

    def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        return False

    def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        return False

    def step_down(self) -> None:
        pass

    def get_leader(self) -> str | None:
        return None

    def on_leadership_change(self, callback) -> None:
        pass


class DummyAsyncLeaderElection(AsyncLeaderElectionPort):
    async def is_leader(self) -> bool:
        return False

    async def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        return False

    async def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        return False

    async def step_down(self) -> None:
        pass

    async def get_leader(self) -> str | None:
        return None

    def on_leadership_change(self, callback) -> None:
        pass


def test_leader_election_port_instantiation():
    obj = DummyLeaderElection()
    assert obj.is_leader() is False
    assert obj.acquire_leadership() is False
    assert obj.renew_leadership() is False
    assert obj.step_down() is None
    assert obj.get_leader() is None
    assert obj.on_leadership_change(lambda a, b: None) is None


@pytest.mark.anyio
async def test_async_leader_election_port_instantiation():
    obj = DummyAsyncLeaderElection()
    assert await obj.is_leader() is False
    assert await obj.acquire_leadership() is False
    assert await obj.renew_leadership() is False
    assert await obj.step_down() is None
    assert await obj.get_leader() is None
    assert obj.on_leadership_change(lambda a, b: None) is None
