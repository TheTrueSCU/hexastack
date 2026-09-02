import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from hexastack_core.ports.leader_election import (
    AsyncLeaderElectionPort,
    LeaderElectionPort,
)

_RENEW_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("pexpire", KEYS[1], ARGV[2])
else
    return 0
end
"""

_STEP_DOWN_LUA_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisLeaderElectionAdapter(LeaderElectionPort):
    """Distributed leader election adapter backed by Redis or Valkey leases.

    Notes/Architectural Intent:
        Implements distributed lease-based active-standby leader election using Redis
        atomic `SET key node_id NX PX ttl_ms` and Lua script heartbeats.
    """

    def __init__(
        self,
        client: Any,
        lease_key: str = "hexastack:leader",
        node_id: str = "node-1",
    ) -> None:
        """Initialize RedisLeaderElectionAdapter.

        Args:
            client: Synchronous Redis/Valkey client instance.
            lease_key: Distributed key representing the active leader lease.
            node_id: Unique identifier for this node.
        """
        self._client = client
        self._lease_key = lease_key
        self._node_id = node_id
        self._is_leader = False
        self._callbacks: list[Callable[[bool, str | None], Any]] = []

    def is_leader(self) -> bool:
        """Check if this node currently holds the leader lease in Redis.

        Returns:
            True if this node is leader, False otherwise.
        """
        return self._is_leader

    def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Attempt to acquire the leader lease.

        Args:
            ttl_seconds: Lease duration in seconds.

        Returns:
            True if acquired, False otherwise.
        """
        px_millis = max(1, int(ttl_seconds * 1000))
        try:
            acquired = bool(
                self._client.set(self._lease_key, self._node_id, nx=True, px=px_millis)
            )
        except Exception:
            acquired = False

        if acquired:
            if not self._is_leader:
                self._is_leader = True
                self._notify_callbacks(True, self._node_id)
            return True

        # Check if already leader
        current = self.get_leader()
        if current == self._node_id:
            # Renew existing lease
            return self.renew_leadership(ttl_seconds)

        if self._is_leader:
            self._is_leader = False
            self._notify_callbacks(False, current)

        return False

    def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Renew the leader lease heartbeat via atomic Lua script.

        Args:
            ttl_seconds: New lease duration in seconds.

        Returns:
            True if renewed, False if lease was lost.
        """
        px_millis = max(1, int(ttl_seconds * 1000))
        try:
            res = self._client.eval(
                _RENEW_LUA_SCRIPT, 1, self._lease_key, self._node_id, px_millis
            )
            renewed = res == 1
        except Exception:
            renewed = False

        if renewed:
            if not self._is_leader:
                self._is_leader = True
                self._notify_callbacks(True, self._node_id)
            return True

        if self._is_leader:
            self._is_leader = False
            self._notify_callbacks(False, self.get_leader())

        return False

    def step_down(self) -> None:
        """Voluntarily release the leader lease in Redis."""
        if self._is_leader:
            with contextlib.suppress(Exception):
                self._client.eval(
                    _STEP_DOWN_LUA_SCRIPT, 1, self._lease_key, self._node_id
                )
            self._is_leader = False
            self._notify_callbacks(False, None)

    def get_leader(self) -> str | None:
        """Retrieve the identifier of the current leader node from Redis.

        Returns:
            Node identifier string of current leader, or None if vacant.
        """
        try:
            raw = self._client.get(self._lease_key)
            if raw is None:
                return None
            return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        except Exception:
            return None

    def on_leadership_change(self, callback: Callable[[bool, str | None], Any]) -> None:
        """Register leadership change listener callback.

        Args:
            callback: Callable receiving (is_leader: bool, leader_id: str | None).
        """
        self._callbacks.append(callback)

    def _notify_callbacks(self, is_leader: bool, leader_id: str | None) -> None:
        """Dispatch leadership transition to registered listeners."""
        for cb in self._callbacks:
            with contextlib.suppress(Exception):
                cb(is_leader, leader_id)


class AsyncRedisLeaderElectionAdapter(AsyncLeaderElectionPort):
    """Asynchronous distributed leader election adapter backed by Redis or Valkey leases.

    Notes/Architectural Intent:
        Coroutine-safe async counterpart to RedisLeaderElectionAdapter for asyncio daemons.
    """

    def __init__(
        self,
        client: Any,
        lease_key: str = "hexastack:leader",
        node_id: str = "async-node-1",
    ) -> None:
        """Initialize AsyncRedisLeaderElectionAdapter.

        Args:
            client: Asynchronous Redis/Valkey client instance (redis.asyncio.Redis).
            lease_key: Distributed key representing the active leader lease.
            node_id: Unique identifier for this node.
        """
        self._client = client
        self._lease_key = lease_key
        self._node_id = node_id
        self._is_leader = False
        self._callbacks: list[Callable[[bool, str | None], Any]] = []

    async def is_leader(self) -> bool:
        """Check if this node currently holds the leader lease in Redis.

        Returns:
            True if this node is leader, False otherwise.
        """
        return self._is_leader

    async def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Attempt to acquire the leader lease asynchronously.

        Args:
            ttl_seconds: Lease duration in seconds.

        Returns:
            True if acquired, False otherwise.
        """
        px_millis = max(1, int(ttl_seconds * 1000))
        try:
            acquired = bool(
                await self._client.set(
                    self._lease_key, self._node_id, nx=True, px=px_millis
                )
            )
        except Exception:
            acquired = False

        if acquired:
            if not self._is_leader:
                self._is_leader = True
                self._notify_callbacks(True, self._node_id)
            return True

        current = await self.get_leader()
        if current == self._node_id:
            return await self.renew_leadership(ttl_seconds)

        if self._is_leader:
            self._is_leader = False
            self._notify_callbacks(False, current)

        return False

    async def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Renew the leader lease heartbeat asynchronously via Lua script.

        Args:
            ttl_seconds: New lease duration in seconds.

        Returns:
            True if renewed, False if lease was lost.
        """
        px_millis = max(1, int(ttl_seconds * 1000))
        try:
            res = await self._client.eval(
                _RENEW_LUA_SCRIPT, 1, self._lease_key, self._node_id, px_millis
            )
            renewed = res == 1
        except Exception:
            renewed = False

        if renewed:
            if not self._is_leader:
                self._is_leader = True
                self._notify_callbacks(True, self._node_id)
            return True

        if self._is_leader:
            self._is_leader = False
            self._notify_callbacks(False, await self.get_leader())

        return False

    async def step_down(self) -> None:
        """Voluntarily release the leader lease in Redis asynchronously."""
        if self._is_leader:
            with contextlib.suppress(Exception):
                await self._client.eval(
                    _STEP_DOWN_LUA_SCRIPT, 1, self._lease_key, self._node_id
                )
            self._is_leader = False
            self._notify_callbacks(False, None)

    async def get_leader(self) -> str | None:
        """Retrieve the identifier of the current leader node from Redis asynchronously.

        Returns:
            Node identifier string of current leader, or None if vacant.
        """
        try:
            raw = await self._client.get(self._lease_key)
            if raw is None:
                return None
            return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        except Exception:
            return None

    def on_leadership_change(self, callback: Callable[[bool, str | None], Any]) -> None:
        """Register leadership change listener callback.

        Args:
            callback: Callable receiving (is_leader: bool, leader_id: str | None).
        """
        self._callbacks.append(callback)

    def _notify_callbacks(self, is_leader: bool, leader_id: str | None) -> None:
        """Dispatch leadership transition to registered listeners."""
        for cb in self._callbacks:
            with contextlib.suppress(Exception):
                res = cb(is_leader, leader_id)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)


__all__ = [
    "AsyncRedisLeaderElectionAdapter",
    "RedisLeaderElectionAdapter",
]
