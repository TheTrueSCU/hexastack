"""Ephemeral background server utility for Playwright and integration testing."""

from __future__ import annotations

import http.client
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


def find_free_port() -> int:
    """Find a dynamically available free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class EphemeralServer:
    """Manages lifecycle of an ephemeral Uvicorn web server running in background."""

    def __init__(self, app_factory_code: str, port: int | None = None) -> None:
        """Initialize ephemeral server with Python factory script code.

        Args:
            app_factory_code: Python code string that creates and runs the ASGI app.
            port: Optional fixed port. If omitted, finds an ephemeral free port.
        """
        self.port = port or find_free_port()
        self.app_factory_code = app_factory_code
        self.proc: subprocess.Popen[Any] | None = None
        self.base_url = f"http://127.0.0.1:{self.port}"

    def start(self, ready_path: str = "/", timeout: float = 10.0) -> str:
        """Start the server process and poll until healthy.

        Args:
            ready_path: Relative URL path to poll for HTTP 200 readiness.
            timeout: Maximum seconds to wait before failing.

        Returns:
            The base URL of the running server.

        Raises:
            RuntimeError: If server fails to start within timeout.
        """
        cmd = [
            sys.executable,
            "-c",
            self.app_factory_code.format(port=self.port),
        ]
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=1.0)
                conn.request("GET", ready_path)
                resp = conn.getresponse()
                if resp.status in (200, 404):  # Responding is ready
                    conn.close()
                    return self.base_url
                conn.close()
            except Exception:
                time.sleep(0.25)

        self.stop()
        raise RuntimeError(f"Ephemeral server failed to start at {self.base_url}")

    def stop(self) -> None:
        """Stop and terminate the background server process."""
        if self.proc is not None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            self.proc = None


@contextmanager
def ephemeral_server(app_factory_code: str, ready_path: str = "/") -> Generator[str]:
    """Context manager launching an ephemeral server on a free port."""
    server = EphemeralServer(app_factory_code)
    try:
        url = server.start(ready_path=ready_path)
        yield url
    finally:
        server.stop()


__all__ = [
    "ephemeral_server",
    "EphemeralServer",
    "find_free_port",
]
