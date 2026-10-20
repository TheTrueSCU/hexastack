"""Ephemeral background server utility for Playwright and integration testing."""

from __future__ import annotations

import http.client
import os
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from typing import IO, Any


def find_free_port() -> int:
    """Find a dynamically available free TCP port on localhost.

    Returns:
        An available integer TCP port number on 127.0.0.1.

    Notes/Architectural Intent:
        Binds to port 0 to allow OS kernel assignment, immediately closing socket
        to return an ephemeral port for test server isolation.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class EphemeralServer:
    """Manages lifecycle of an ephemeral Uvicorn web server running in background."""

    def __init__(
        self,
        app_factory_code: str,
        port: int | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        """Initialize ephemeral server with Python factory script code.

        Args:
            app_factory_code: Python code string that creates and runs the ASGI app.
            port: Optional fixed port. If omitted, finds an ephemeral free port.
            env: Optional environment variables dictionary for subprocess.

        Notes/Architectural Intent:
            Configures process environment and binds to an ephemeral port to provide
            isolated background server processes for integration and E2E browser tests.
        """
        self.port = port or find_free_port()
        self.app_factory_code = app_factory_code
        self.env = env
        self.proc: subprocess.Popen[Any] | None = None
        self._log_file: IO[str] | None = None
        self.base_url = f"http://127.0.0.1:{self.port}"

    def start(self, ready_path: str = "/", timeout: float = 30.0) -> str:
        """Start the server process and poll until healthy.

        Args:
            ready_path: Relative URL path to poll for HTTP readiness.
            timeout: Maximum seconds to wait before failing (default: 30.0s).

        Returns:
            The base URL of the running server.

        Raises:
            RuntimeError: If server exits prematurely or fails to start within timeout.

        Notes/Architectural Intent:
            Spawns background Uvicorn/ASGI process with captured stdout and stderr in a
            temporary file. Continuously monitors process health and readiness endpoint,
            failing immediately with complete diagnostic logs if the subprocess crashes.
        """
        cmd = [
            sys.executable,
            "-c",
            self.app_factory_code.format(port=self.port),
        ]
        proc_env = dict(os.environ)
        if self.env:
            proc_env.update(self.env)

        self._log_file = tempfile.TemporaryFile(mode="w+t", encoding="utf-8")  # noqa: SIM115
        self.proc = subprocess.Popen(
            cmd,
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
            env=proc_env,
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.proc.poll() is not None:
                returncode = self.proc.returncode
                log_output = self._read_logs()
                self.stop()
                raise RuntimeError(
                    f"Ephemeral server failed to start at {self.base_url} "
                    f"(process exited prematurely with code {returncode}):\n{log_output}"
                )

            try:
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1.0)
                conn.request("GET", ready_path)
                resp = conn.getresponse()
                if resp.status in (200, 301, 302, 307, 308, 404):  # Responding is ready
                    conn.close()
                    return self.base_url
                conn.close()
            except Exception:
                time.sleep(0.25)

        log_output = self._read_logs()
        self.stop()
        raise RuntimeError(
            f"Ephemeral server failed to start at {self.base_url} within {timeout}s:\n{log_output}"
        )

    def _read_logs(self) -> str:
        """Read captured stdout/stderr logs from the temporary log file.

        Returns:
            String contents of captured subprocess logs.

        Notes/Architectural Intent:
            Flushes and rewinds the temporary log file to safely inspect output without blocking.
        """
        if self._log_file is not None:
            with suppress(Exception):
                self._log_file.flush()
                self._log_file.seek(0)
                return self._log_file.read().strip()
        return ""

    def stop(self) -> None:
        """Stop and terminate the background server process.

        Notes/Architectural Intent:
            Sends SIGTERM, waits gracefully, and falls back to SIGKILL to guarantee
            no orphan subprocesses linger in testing environments. Cleans up log file.
        """
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None

        if self._log_file is not None:
            with suppress(Exception):
                self._log_file.close()
            self._log_file = None


@contextmanager
def ephemeral_server(
    app_factory_code: str,
    ready_path: str = "/",
    env: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> Generator[str]:
    """Context manager launching an ephemeral server on a free port.

    Args:
        app_factory_code: Python code string creating and launching the ASGI server.
        ready_path: Relative URL path to poll for HTTP readiness.
        env: Optional environment variables dictionary for subprocess.
        timeout: Maximum seconds to wait for server readiness (default: 30.0s).

    Yields:
        The base URL of the running server.

    Raises:
        RuntimeError: If server fails to start within timeout.

    Notes/Architectural Intent:
        Wraps EphemeralServer in a context manager to ensure guaranteed process shutdown.
    """
    server = EphemeralServer(app_factory_code, env=env)
    try:
        url = server.start(ready_path=ready_path, timeout=timeout)
        yield url
    finally:
        server.stop()


__all__ = [
    "ephemeral_server",
    "EphemeralServer",
    "find_free_port",
]
