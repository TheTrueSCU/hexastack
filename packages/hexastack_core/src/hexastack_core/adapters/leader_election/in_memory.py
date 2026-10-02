import asyncio
import contextlib
from collections.abc import Callable
from typing import Any

from hexastack_core.ports.leader_election import (
    AsyncLeaderElectionPort,
    LeaderElectionPort,
)


class SingleProcessLeaderElection(LeaderElectionPort):
    """Single-process leader election adapter.

    Notes/Architectural Intent:
        Always elects the host node as leader. Perfect for standalone local deployments,
        CLI applications, and unit test environments where clustering is not needed.
    """

    def __init__(self, node_id: str = "node-1") -> None:
        """Initialize SingleProcessLeaderElection.

        Args:
            node_id: Unique identifier for this node.
        """
        self._node_id = node_id
        self._is_leader = False
        self._callbacks: list[Callable[[bool, str | None], Any]] = []

    def is_leader(self) -> bool:
        """Check if this instance is leader.

        Returns:
            True if leader, False otherwise.
        """
        return self._is_leader

    def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Acquire leadership unconditionally for this process.

        Args:
            ttl_seconds: Lease duration (ignored for single process).

        Returns:
            True.
        """
        if not self._is_leader:
            self._is_leader = True
            self._notify_callbacks(True, self._node_id)
        return True

    def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Renew leadership lease.

        Args:
            ttl_seconds: Lease duration.

        Returns:
            True if currently leader, False otherwise.
        """
        return self._is_leader

    def step_down(self) -> None:
        """Step down from leadership."""
        if self._is_leader:
            self._is_leader = False
            self._notify_callbacks(False, None)

    def get_leader(self) -> str | None:
        """Get current leader node identifier.

        Returns:
            Node identifier if leader, None otherwise.
        """
        return self._node_id if self._is_leader else None

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


class AsyncSingleProcessLeaderElection(AsyncLeaderElectionPort):
    """Asynchronous single-process leader election adapter.

    Notes/Architectural Intent:
        Async counterpart to SingleProcessLeaderElection for asyncio-based daemons.
    """

    def __init__(self, node_id: str = "async-node-1") -> None:
        """Initialize AsyncSingleProcessLeaderElection.

        Args:
            node_id: Unique identifier for this node.
        """
        self._node_id = node_id
        self._is_leader = False
        self._callbacks: list[Callable[[bool, str | None], Any]] = []

    async def is_leader(self) -> bool:
        """Check if this instance is leader.

        Returns:
            True if leader, False otherwise.
        """
        return self._is_leader

    async def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Acquire leadership asynchronously.

        Args:
            ttl_seconds: Lease duration.

        Returns:
            True.
        """
        if not self._is_leader:
            self._is_leader = True
            self._notify_callbacks(True, self._node_id)
        return True

    async def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Renew leadership lease asynchronously.

        Args:
            ttl_seconds: Lease duration.

        Returns:
            True if currently leader, False otherwise.
        """
        return self._is_leader

    async def step_down(self) -> None:
        """Step down from leadership asynchronously."""
        if self._is_leader:
            self._is_leader = False
            self._notify_callbacks(False, None)

    async def get_leader(self) -> str | None:
        """Get current leader node identifier.

        Returns:
            Node identifier if leader, None otherwise.
        """
        return self._node_id if self._is_leader else None

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
    "AsyncSingleProcessLeaderElection",
    "SingleProcessLeaderElection",
]
