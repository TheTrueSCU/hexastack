import inspect

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


def test_leader_election_port_is_abstract() -> None:
    """Verify that LeaderElectionPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(LeaderElectionPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        LeaderElectionPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_leader_election_port_abstract_methods() -> None:
    """Verify abstract methods on LeaderElectionPort."""
    expected = {
        "acquire_leadership",
        "get_leader",
        "is_leader",
        "on_leadership_change",
        "renew_leadership",
        "step_down",
    }
    abstracts = LeaderElectionPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0


def test_async_leader_election_port_is_abstract() -> None:
    """Verify that AsyncLeaderElectionPort cannot be instantiated directly and is abstract."""
    is_abs = inspect.isabstract(AsyncLeaderElectionPort)
    assert is_abs is True
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AsyncLeaderElectionPort()  # ty: ignore[call-non-callable] # type: ignore[abstract]


def test_async_leader_election_port_abstract_methods() -> None:
    """Verify abstract methods on AsyncLeaderElectionPort."""
    expected = {
        "acquire_leadership",
        "get_leader",
        "is_leader",
        "on_leadership_change",
        "renew_leadership",
        "step_down",
    }
    abstracts = AsyncLeaderElectionPort.__abstractmethods__
    diff = expected.difference(abstracts)
    assert len(diff) == 0
