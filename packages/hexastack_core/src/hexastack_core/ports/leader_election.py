from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class LeaderElectionPort(ABC):
    """Abstract interface defining distributed leader election and active lease coordination.

    Notes/Architectural Intent:
        Decouples distributed services, outbox daemons, active-standby cluster workers,
        and stream consumers from specific consensus backends (e.g., Redis/Valkey atomic lease,
        Consul, etcd, Kubernetes lease objects).
    """

    @abstractmethod
    def is_leader(self) -> bool:
        """Check if the current process / node instance currently holds leadership.

        Returns:
            True if this instance is the active leader, False otherwise.
        """

    @abstractmethod
    def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Attempt to acquire leadership lease.

        Args:
            ttl_seconds: Lease duration in seconds before expiration if not renewed.

        Returns:
            True if leadership was successfully acquired, False otherwise.
        """

    @abstractmethod
    def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Renew leadership lease heartbeat for another TTL interval.

        Args:
            ttl_seconds: New lease duration in seconds.

        Returns:
            True if renewed, False if leadership was lost or taken by another instance.
        """

    @abstractmethod
    def step_down(self) -> None:
        """Voluntarily relinquish leadership lease, allowing other standby nodes to elect."""

    @abstractmethod
    def get_leader(self) -> str | None:
        """Retrieve the identifier of the current elected leader node, if any.

        Returns:
            Node identifier string of current leader, or None if vacant.
        """

    @abstractmethod
    def on_leadership_change(self, callback: Callable[[bool, str | None], Any]) -> None:
        """Register a callback invoked when leadership state changes.

        Args:
            callback: Callable accepting (is_leader: bool, leader_id: str | None).
        """


class AsyncLeaderElectionPort(ABC):
    """Abstract interface defining asynchronous distributed leader election coordination.

    Notes/Architectural Intent:
        Async counterpart to LeaderElectionPort for asyncio-native daemons and background tasks.
    """

    @abstractmethod
    async def is_leader(self) -> bool:
        """Check if the current instance currently holds leadership asynchronously.

        Returns:
            True if this instance is the active leader, False otherwise.
        """

    @abstractmethod
    async def acquire_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Attempt to acquire leadership lease asynchronously.

        Args:
            ttl_seconds: Lease duration in seconds.

        Returns:
            True if leadership was successfully acquired, False otherwise.
        """

    @abstractmethod
    async def renew_leadership(self, ttl_seconds: float = 10.0) -> bool:
        """Renew leadership lease heartbeat asynchronously.

        Args:
            ttl_seconds: New lease duration in seconds.

        Returns:
            True if renewed, False if leadership was lost.
        """

    @abstractmethod
    async def step_down(self) -> None:
        """Voluntarily relinquish leadership lease asynchronously."""

    @abstractmethod
    async def get_leader(self) -> str | None:
        """Retrieve the identifier of the current elected leader node asynchronously.

        Returns:
            Node identifier string of current leader, or None if vacant.
        """

    @abstractmethod
    def on_leadership_change(self, callback: Callable[[bool, str | None], Any]) -> None:
        """Register a callback invoked when leadership state changes.

        Args:
            callback: Callable accepting (is_leader: bool, leader_id: str | None).
        """


__all__ = [
    "AsyncLeaderElectionPort",
    "LeaderElectionPort",
]
