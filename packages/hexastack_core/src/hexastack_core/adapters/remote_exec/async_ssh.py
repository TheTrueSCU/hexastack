"""Asynchronous SSH remote execution and file transfer adapter powered by AsyncSSH.

Notes/Architectural Intent:
    Implements RemoteExecutionPort using asyncssh for non-blocking event-loop-safe remote shell
    execution, real-time stdout/stderr streaming, and SFTP file operations.
    Maintains zero open listening ports on the caller and supports Ed25519/RSA keys, certificates,
    and password authentication without blocking thread pools.
"""

import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from hexastack_core.ports.remote_exec import RemoteExecResult, RemoteExecutionPort


class AsyncSshAdapter(RemoteExecutionPort):
    """Non-blocking SSH remote execution adapter utilizing AsyncSSH.

    Notes/Architectural Intent:
        Wraps asyncssh connections with robust lifecycle management, connection reuse,
        configurable timeouts, environment variable scoping, and SFTP transfers.
    """

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str | None = None,
        client_keys: list[str | Path] | None = None,
        password: str | None = None,
        known_hosts: Any | None = (),
        connect_timeout: float = 30.0,
        connection: Any | None = None,
    ) -> None:
        """Initialize the AsyncSSH remote execution adapter.

        Args:
            host: Target remote hostname or IP address.
            port: SSH port on remote host.
            username: Remote login username.
            client_keys: Optional list of private key paths or key data.
            password: Optional password for password authentication.
            known_hosts: Path to known_hosts file, or () to disable strict host key checking.
            connect_timeout: Connection timeout in seconds.
            connection: Optional pre-established asyncssh connection to reuse.
        """
        self.host = host
        self.port = port
        self.username = username
        self.client_keys = client_keys
        self.password = password
        self.known_hosts = known_hosts
        self.connect_timeout = connect_timeout
        self._connection = connection

    def _get_asyncssh(self) -> Any:
        """Dynamically import asyncssh or raise an informative ImportError.

        Returns:
            The imported asyncssh module.

        Raises:
            ImportError: If asyncssh is not installed.
        """
        try:
            import asyncssh

            return asyncssh
        except ImportError as err:
            raise ImportError(
                "The 'asyncssh' package is required for AsyncSshAdapter. "
                "Install it via 'uv add hexastack-core[ssh]' or 'pip install asyncssh'."
            ) from err

    async def get_connection(self) -> Any:
        """Get or lazily establish the persistent asyncssh connection.

        Returns:
            Active asyncssh.SSHClientConnection instance.
        """
        if self._connection is not None:
            return self._connection

        asyncssh = self._get_asyncssh()
        conn = await asyncssh.connect(
            self.host,
            port=self.port,
            username=self.username,
            client_keys=self.client_keys,
            password=self.password,
            known_hosts=self.known_hosts,
            login_timeout=self.connect_timeout,
        )
        self._connection = conn
        return self._connection

    async def close(self) -> None:
        """Close the underlying SSH connection if opened."""
        if self._connection is not None:
            self._connection.close()
            await self._connection.wait_closed()
            self._connection = None

    async def __aenter__(self) -> "AsyncSshAdapter":
        """Enter async context manager, establishing connection."""
        await self.get_connection()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context manager, closing connection."""
        await self.close()

    def _prepare_command(
        self,
        command: str,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ) -> str:
        """Compose remote command string prefixing environment variables and working directory.

        Args:
            command: Base shell command.
            env: Optional environment variables dictionary.
            cwd: Optional working directory.

        Returns:
            Fully qualified shell command line string.
        """
        parts: list[str] = []
        if env:
            for k, v in env.items():
                # Escape double quotes in value
                escaped_v = v.replace('"', '\\"')
                parts.append(f'export {k}="{escaped_v}"')
        if cwd:
            parts.append(f"cd {cwd}")
        parts.append(command)
        return " && ".join(parts)

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
            env: Optional environment variables to export.
            cwd: Optional working directory.

        Returns:
            RemoteExecResult containing exit status, stdout, stderr, and duration.
        """
        conn = await self.get_connection()
        full_cmd = self._prepare_command(command, env=env, cwd=cwd)

        start_time = time.perf_counter()
        result = await conn.run(full_cmd, timeout=timeout_seconds, check=False)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return RemoteExecResult(
            exit_status=result.exit_status or 0,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            duration_ms=duration_ms,
        )

    async def stream_output(
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
            Chunks of stdout/stderr as strings.
        """
        conn = await self.get_connection()
        full_cmd = self._prepare_command(command, env=env, cwd=cwd)

        async with conn.create_process(full_cmd) as process:
            while True:
                chunk = await process.stdout.read(4096)
                if not chunk:
                    break
                yield chunk

    async def upload_file(
        self,
        local_path: str,
        remote_path: str,
    ) -> None:
        """Upload a local file to the remote target via SFTP.

        Args:
            local_path: Local filesystem path to source file.
            remote_path: Destination path on the remote host.

        Raises:
            FileNotFoundError: If local_path does not exist.
        """
        path = Path(local_path)
        if not path.is_file():
            raise FileNotFoundError(f"Local file not found: {local_path}")

        conn = await self.get_connection()
        async with conn.start_sftp_client() as sftp:
            await sftp.put(str(path), remote_path)

    async def download_file(
        self,
        remote_path: str,
        local_path: str,
    ) -> None:
        """Download a remote file to the local filesystem via SFTP.

        Args:
            remote_path: Source file path on the remote host.
            local_path: Local filesystem destination path.
        """
        conn = await self.get_connection()
        async with conn.start_sftp_client() as sftp:
            await sftp.get(remote_path, local_path)


__all__ = [
    "AsyncSshAdapter",
]
