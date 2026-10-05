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
    # Callback that raises should be suppressed
    election.on_leadership_change(lambda is_lead, lead_id: 1 / 0)

    # Step down when not leader is a no-op
    election.step_down()
    assert changes == []

    # Renew when not leader returns False
    assert election.renew_leadership() is False

    # Acquire
    assert election.acquire_leadership() is True
    assert election.is_leader() is True
    assert election.get_leader() == "master-node"
    assert changes == [(True, "master-node")]

    # Re-acquire when already leader is no-op for notifications
    assert election.acquire_leadership() is True
    assert changes == [(True, "master-node")]

    # Renew
    assert election.renew_leadership() is True

    # Step down
    election.step_down()
    assert election.is_leader() is False
    assert election.get_leader() is None
    assert changes == [(True, "master-node"), (False, None)]


def test_single_process_leader_election_defaults():
    election = SingleProcessLeaderElection()
    assert election.is_leader() is False
    assert election.acquire_leadership() is True
    assert election.get_leader() == "node-1"


@pytest.mark.anyio
async def test_async_single_process_leader_election_lifecycle():
    election = AsyncSingleProcessLeaderElection(node_id="async-master-node")
    assert await election.is_leader() is False
    assert await election.get_leader() is None

    changes: list[tuple[bool, str | None]] = []
    async_changes: list[tuple[bool, str | None]] = []

    def sync_cb(is_lead: bool, lead_id: str | None):
        changes.append((is_lead, lead_id))

    async def async_cb(is_lead: bool, lead_id: str | None):
        async_changes.append((is_lead, lead_id))

    def failing_cb(is_lead: bool, lead_id: str | None):
        raise RuntimeError("boom")

    election.on_leadership_change(sync_cb)
    election.on_leadership_change(async_cb)
    election.on_leadership_change(failing_cb)

    # Step down when not leader is a no-op
    await election.step_down()
    assert changes == []

    # Renew when not leader returns False
    assert await election.renew_leadership() is False

    # Acquire
    assert await election.acquire_leadership() is True
    assert await election.is_leader() is True
    assert await election.get_leader() == "async-master-node"
    assert changes == [(True, "async-master-node")]

    # Re-acquire when already leader
    assert await election.acquire_leadership() is True
    assert changes == [(True, "async-master-node")]

    # Renew
    assert await election.renew_leadership() is True

    # Step down
    await election.step_down()
    assert await election.is_leader() is False
    assert await election.get_leader() is None
    assert changes == [(True, "async-master-node"), (False, None)]


@pytest.mark.anyio
async def test_async_single_process_leader_election_defaults():
    election = AsyncSingleProcessLeaderElection()
    assert await election.is_leader() is False
    assert await election.acquire_leadership() is True
    assert await election.get_leader() == "async-node-1"
