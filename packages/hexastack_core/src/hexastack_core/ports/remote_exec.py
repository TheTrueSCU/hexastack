"""Abstract port definitions for non-blocking remote execution and file transfer.

Notes/Architectural Intent:
    Decouples distributed execution engines, remote deployment workflows, and batch schedulers
    from concrete transport protocols (SSH, AsyncSSH, Docker exec, ephemeral bastions).
    Mandates non-blocking coroutines and async iterators to preserve event-loop concurrency.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class RemoteExecResult:
    """Execution outcome of a remote shell command.

    Notes/Architectural Intent:
        Encapsulates standard POSIX process termination attributes, capturing standard output,
        error streams, exit codes, and elapsed execution timing without external process leaks.
    """

    exit_status: int
    stdout: str
    stderr: str
    duration_ms: float


class RemoteExecutionPort(ABC):
    """Abstract port for non-blocking remote shell invocation and file transfers.

    Notes/Architectural Intent:
        Enables distributed clusters, batch runners, and remote automation pipelines to
        execute commands and transfer files asynchronously without stalling the Python event loop.
    """

    @abstractmethod
    async def run(
        self,
        command: str,
        *,
        timeout_seconds: float = 60.0,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> RemoteExecResult:
        """Execute a remote shell command and await complete execution.

        Args:
            command: Shell command string to execute remotely.
            timeout_seconds: Maximum allowed execution duration in seconds.
            env: Optional environment variables to export for the command process.
            cwd: Optional working directory to switch into before execution.

        Returns:
            RemoteExecResult containing exit status, captured stdout/stderr, and duration.

        Raises:
            TimeoutError: If execution exceeds timeout_seconds.
            ConnectionError: If remote channel drops or transport fails.
        """

    @abstractmethod
    def stream_output(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream remote command stdout/stderr chunks asynchronously in real-time.

        Args:
            command: Shell command string to execute remotely.
            env: Optional environment variables to export.
            cwd: Optional working directory.

        Yields:
            Chunks of stdout/stderr as strings as they arrive from the remote process.

        Raises:
            ConnectionError: If the remote session terminates prematurely.
        """

    @abstractmethod
    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> None:
        """Upload a local file to the remote target via secure file transfer.

        Args:
            local_path: Local filesystem path to source file.
            remote_path: Destination path on the remote host.

        Raises:
            FileNotFoundError: If local_path does not exist.
            ConnectionError: If file transfer fails.
        """

    @abstractmethod
    async def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> None:
        """Download a remote file to the local filesystem.

        Args:
            remote_path: Source file path on the remote host.
            local_path: Local filesystem destination path.

        Raises:
            FileNotFoundError: If remote_path does not exist remotely.
            ConnectionError: If file transfer fails.
        """


__all__ = [
    "RemoteExecResult",
    "RemoteExecutionPort",
]
