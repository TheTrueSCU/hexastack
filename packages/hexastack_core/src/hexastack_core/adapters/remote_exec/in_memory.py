"""In-memory simulation adapter for remote command execution and file transfer.

Notes/Architectural Intent:
    Serves as the deterministic reference implementation of RemoteExecutionPort for hermetic
    testing, mocking, and property-based differential verification without opening network sockets.
"""

from collections.abc import AsyncIterator
from pathlib import Path

from hexastack_core.ports.remote_exec import RemoteExecResult, RemoteExecutionPort


class InMemoryRemoteExecutionAdapter(RemoteExecutionPort):
    """In-memory simulated remote execution adapter.

    Notes/Architectural Intent:
        Maintains an in-memory virtual filesystem and a table of scripted responses for
        simulated remote commands. Records command invocations for assertion checking.
    """

    def __init__(
        self,
        default_exit_status: int = 0,
        default_stdout: str = "",
        default_stderr: str = "",
        default_duration_ms: float = 1.0,
    ) -> None:
        """Initialize the in-memory execution adapter with default outcomes.

        Args:
            default_exit_status: Default exit code returned for unscripted commands.
            default_stdout: Default stdout returned for unscripted commands.
            default_stderr: Default stderr returned for unscripted commands.
            default_duration_ms: Default simulated execution time in milliseconds.
        """
        self.default_exit_status = default_exit_status
        self.default_stdout = default_stdout
        self.default_stderr = default_stderr
        self.default_duration_ms = default_duration_ms

        self._responses: dict[str, RemoteExecResult] = {}
        self._stream_chunks: dict[str, list[str]] = {}
        self._executed_commands: list[str] = []
        self._virtual_files: dict[str, bytes] = {}

    @property
    def executed_commands(self) -> list[str]:
        """List of all commands executed against this adapter in chronological order."""
        return list(self._executed_commands)

    @property
    def virtual_files(self) -> dict[str, bytes]:
        """Dictionary of virtual remote files stored in this adapter."""
        return dict(self._virtual_files)

    def register_command(
        self,
        command: str,
        exit_status: int = 0,
        stdout: str = "",
        stderr: str = "",
        duration_ms: float = 1.0,
        chunks: list[str] | None = None,
    ) -> None:
        """Register a scripted response for a specific remote command string.

        Args:
            command: The command line to match.
            exit_status: Process exit status code.
            stdout: Captured standard output.
            stderr: Captured standard error.
            duration_ms: Simulated execution duration in milliseconds.
            chunks: Optional list of stream chunks yielded during stream_output.
        """
        self._responses[command] = RemoteExecResult(
            exit_status=exit_status,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
        )
        if chunks is not None:
            self._stream_chunks[command] = list(chunks)

    async def run(
        self,
        command: str,
        *,
        timeout_seconds: float = 60.0,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> RemoteExecResult:
        """Execute a simulated remote command.

        Args:
            command: Shell command to execute.
            timeout_seconds: Timeout bound (unused in simulation).
            env: Optional environment variables.
            cwd: Optional working directory.

        Returns:
            The registered RemoteExecResult or the configured default result.
        """
        self._executed_commands.append(command)
        if command in self._responses:
            return self._responses[command]
        return RemoteExecResult(
            exit_status=self.default_exit_status,
            stdout=self.default_stdout,
            stderr=self.default_stderr,
            duration_ms=self.default_duration_ms,
        )

    async def stream_output(
        self,
        command: str,
        *,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream simulated stdout/stderr chunks asynchronously.

        Args:
            command: Shell command to stream.
            env: Optional environment variables.
            cwd: Optional working directory.

        Yields:
            Chunks of stdout/stderr as strings.
        """
        self._executed_commands.append(command)
        if command in self._stream_chunks:
            for chunk in self._stream_chunks[command]:
                yield chunk
        elif command in self._responses:
            yield self._responses[command].stdout
        else:
            if self.default_stdout:
                yield self.default_stdout

    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> None:
        """Upload a local file to the simulated remote virtual filesystem.

        Args:
            local_path: Local filesystem path to read.
            remote_path: Target virtual path.

        Raises:
            FileNotFoundError: If local_path does not exist on disk.
        """
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        content = path.read_bytes()
        self._virtual_files[remote_path] = content

    async def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> None:
        """Download a file from the simulated remote virtual filesystem to local disk.

        Args:
            remote_path: Source path in virtual filesystem.
            local_path: Destination local path on disk.

        Raises:
            FileNotFoundError: If remote_path is not in virtual filesystem.
        """
        if remote_path not in self._virtual_files:
            raise FileNotFoundError(f"Remote virtual file not found: {remote_path}")
        content = self._virtual_files[remote_path]
        target = Path(local_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


__all__ = [
    "InMemoryRemoteExecutionAdapter",
]
