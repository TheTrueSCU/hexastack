import pytest

from hexastack_core.adapters.leader_election import (
    AsyncSingleProcessLeaderElection,
    SingleProcessLeaderElection,
)
from hexastack_core.ports.leader_election import (
    AsyncLeaderElectionPort,
    LeaderElectionPort,
)


def test_leader_election_port_instantiation():
    obj: LeaderElectionPort = SingleProcessLeaderElection(node_id="node-1")
    assert obj.is_leader() is False
    assert obj.acquire_leadership() is True
    assert obj.is_leader() is True
    assert obj.renew_leadership() is True
    assert obj.get_leader() == "node-1"
    obj.step_down()
    assert obj.is_leader() is False


@pytest.mark.anyio
async def test_async_leader_election_port_instantiation():
    obj: AsyncLeaderElectionPort = AsyncSingleProcessLeaderElection(
        node_id="async-node-1"
    )
    assert await obj.is_leader() is False
    assert await obj.acquire_leadership() is True
    assert await obj.is_leader() is True
    assert await obj.renew_leadership() is True
    assert await obj.get_leader() == "async-node-1"
    await obj.step_down()
    assert await obj.is_leader() is False
