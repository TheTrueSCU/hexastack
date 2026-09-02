import pytest

from hexastack_core.adapters.leader_election.in_memory import (
    AsyncSingleProcessLeaderElection,
    SingleProcessLeaderElection,
)


def test_single_process_leader_election_lifecycle():
    election = SingleProcessLeaderElection(node_id="master-node")
    assert election.is_leader() is False
    assert election.get_leader() is None

    changes: list[tuple[bool, str | None]] = []
    election.on_leadership_change(
        lambda is_lead, lead_id: changes.append((is_lead, lead_id))
    )

    # Acquire
    assert election.acquire_leadership() is True
    assert election.is_leader() is True
    assert election.get_leader() == "master-node"
    assert changes == [(True, "master-node")]

    # Renew
    assert election.renew_leadership() is True

    # Step down
    election.step_down()
    assert election.is_leader() is False
    assert election.get_leader() is None
    assert changes == [(True, "master-node"), (False, None)]


@pytest.mark.anyio
async def test_async_single_process_leader_election_lifecycle():
    election = AsyncSingleProcessLeaderElection(node_id="async-master-node")
    assert await election.is_leader() is False
    assert await election.get_leader() is None

    changes: list[tuple[bool, str | None]] = []
    election.on_leadership_change(
        lambda is_lead, lead_id: changes.append((is_lead, lead_id))
    )

    # Acquire
    assert await election.acquire_leadership() is True
    assert await election.is_leader() is True
    assert await election.get_leader() == "async-master-node"
    assert changes == [(True, "async-master-node")]

    # Renew
    assert await election.renew_leadership() is True

    # Step down
    await election.step_down()
    assert await election.is_leader() is False
    assert await election.get_leader() is None
    assert changes == [(True, "async-master-node"), (False, None)]
