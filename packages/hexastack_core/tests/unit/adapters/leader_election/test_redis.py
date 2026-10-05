from unittest.mock import AsyncMock, MagicMock

import pytest

from hexastack_core.adapters.leader_election.redis import (
    AsyncRedisLeaderElectionAdapter,
    RedisLeaderElectionAdapter,
)


def test_redis_leader_election_sync_lifecycle():
    mock_redis = MagicMock()
    # Test default initialization
    default_election = RedisLeaderElectionAdapter(mock_redis)
    assert default_election._lease_key == "hexastack:leader"
    assert default_election._node_id == "node-1"
    assert default_election.is_leader() is False

    # 1. Acquire succeeds (SET NX returns True)
    mock_redis.set.return_value = True
    # 2. Renew succeeds (eval returns 1)
    mock_redis.eval.return_value = 1
    # 3. get_leader returns node_id
    mock_redis.get.return_value = b"node-alpha"

    election = RedisLeaderElectionAdapter(
        mock_redis, lease_key="lease:main", node_id="node-alpha"
    )

    changes: list[tuple[bool, str | None]] = []
    # Test callback that raises exception (should be safely suppressed)
    election.on_leadership_change(
        lambda is_l, l_id: (_ for _ in ()).throw(RuntimeError("cb error"))
    )
    election.on_leadership_change(
        lambda is_lead, lead_id: changes.append((is_lead, lead_id))
    )

    # Acquire
    assert election.acquire_leadership(ttl_seconds=5.0) is True
    assert election.is_leader() is True
    assert election.get_leader() == "node-alpha"
    assert len(changes) == 1
    assert changes[0] == (True, "node-alpha")

    # Renew with custom TTL
    assert election.renew_leadership(ttl_seconds=3.0) is True

    # Step down
    election.step_down()
    assert election.is_leader() is False
    assert len(changes) == 2
    assert changes[1] == (False, None)

    # Calling step_down again when not leader is a no-op
    election.step_down()
    assert len(changes) == 2


def test_redis_leader_election_contention():
    mock_redis = MagicMock()
    # SET NX fails because another leader holds the lease
    mock_redis.set.return_value = False
    mock_redis.get.return_value = b"node-beta"

    election = RedisLeaderElectionAdapter(
        mock_redis, lease_key="lease:main", node_id="node-alpha"
    )

    assert election.acquire_leadership() is False
    assert election.is_leader() is False
    assert election.get_leader() == "node-beta"


@pytest.mark.anyio
async def test_async_redis_leader_election_lifecycle():
    mock_redis = MagicMock()
    # Test default initialization
    default_async_election = AsyncRedisLeaderElectionAdapter(mock_redis)
    assert default_async_election._lease_key == "hexastack:leader"
    assert default_async_election._node_id == "async-node-1"
    assert await default_async_election.is_leader() is False

    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.eval = AsyncMock(return_value=1)
    mock_redis.get = AsyncMock(return_value=b"async-node-alpha")

    election = AsyncRedisLeaderElectionAdapter(
        mock_redis, lease_key="lease:async", node_id="async-node-alpha"
    )

    changes: list[tuple[bool, str | None]] = []

    async def async_cb(is_lead: bool, lead_id: str | None) -> None:
        changes.append((is_lead, lead_id))

    election.on_leadership_change(async_cb)

    assert await election.acquire_leadership(ttl_seconds=5.0) is True
    assert await election.is_leader() is True
    assert await election.get_leader() == "async-node-alpha"

    assert await election.renew_leadership(ttl_seconds=3.0) is True

    await election.step_down()
    assert await election.is_leader() is False
    # Additional step_down when not leader is a no-op
    await election.step_down()


def test_redis_leader_election_reacquire_and_loss():
    mock_redis = MagicMock()
    election = RedisLeaderElectionAdapter(mock_redis, node_id="node-1")

    # 1. SET fails on lease contention, but get_leader returns self -> renews
    mock_redis.set.return_value = False
    mock_redis.get.return_value = b"node-1"
    mock_redis.eval.return_value = 1
    assert election.acquire_leadership() is True
    assert election.is_leader() is True

    # 2. Renew fails (lost lease) -> transitions to not leader
    mock_redis.eval.return_value = 0
    mock_redis.get.return_value = b"node-2"
    assert election.renew_leadership() is False
    assert election.is_leader() is False

    # 3. Exception in get_leader -> returns None
    mock_redis.get.side_effect = RuntimeError("Redis down")
    assert election.get_leader() is None


@pytest.mark.anyio
async def test_async_redis_leader_election_reacquire_and_loss():
    mock_redis = MagicMock()
    election = AsyncRedisLeaderElectionAdapter(mock_redis, node_id="async-node-1")

    mock_redis.set = AsyncMock(return_value=False)
    mock_redis.get = AsyncMock(return_value=b"async-node-1")
    mock_redis.eval = AsyncMock(return_value=1)
    assert await election.acquire_leadership() is True
    assert await election.is_leader() is True

    mock_redis.eval = AsyncMock(return_value=0)
    mock_redis.get = AsyncMock(return_value=b"async-node-2")
    assert await election.renew_leadership() is False
    assert await election.is_leader() is False

    mock_redis.get = AsyncMock(side_effect=RuntimeError("Redis down"))
    assert await election.get_leader() is None
