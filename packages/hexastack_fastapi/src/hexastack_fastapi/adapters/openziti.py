"""Zero-Trust Dark Microservice ASGI presentation adapter using OpenZiti.

Notes/Architectural Intent:
    Enables FastAPI/Starlette applications to host services directly on an OpenZiti overlay
    network fabric without opening listening TCP sockets or exposed host ports.
    Uses outbound-only mTLS tunnels so services remain dark and invisible to LAN scans
    and the public internet.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable, Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "openziti_bind",
    "OpenZitiASGIAdapter",
    "OpenZitiConfig",
]


@dataclass(frozen=True, slots=True)
class OpenZitiConfig:
    """Configuration for hosting an ASGI application over the OpenZiti overlay network.

    Args:
        identity_path: Path to the enrolled OpenZiti identity JSON credentials file.
        service_name: Name of the OpenZiti service configured with Bind permissions.
        bind_host: Virtual hostname or IP for the intercepted socket. Defaults to '127.0.0.1'.
        bind_port: Virtual port for the intercepted socket. Defaults to 8000.
        enabled: Whether OpenZiti overlay hosting is active. Defaults to True.

    Notes/Architectural Intent:
        The bind_host and bind_port do not open listening kernel ports on the host.
        They serve as the socket binding hook intercepted by OpenZiti's monkeypatch layer.
    """

    identity_path: Path | str
    service_name: str
    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    enabled: bool = True

    def resolved_identity_path(self) -> Path:
        """Resolve and validate the OpenZiti identity credentials file path.

        Returns:
            Resolved Path object pointing to the identity file.

        Raises:
            FileNotFoundError: If the identity credentials file does not exist on disk.
        """
        path = Path(self.identity_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(
                f"OpenZiti identity credentials file not found: {self.identity_path}"
            )
        return path


class OpenZitiASGIAdapter:
    """ASGI server adapter enabling zero-trust hosting on the OpenZiti overlay fabric.

    Notes/Architectural Intent:
        Wraps Python socket operations via OpenZiti's monkeypatching infrastructure to bind
        ASGI servers (e.g. Uvicorn) directly to an OpenZiti service without opening listening
        network sockets on the host OS.
    """

    def __init__(self, config: OpenZitiConfig) -> None:
        """Initialize the OpenZiti ASGI adapter.

        Args:
            config: OpenZitiConfig specifying identity path, service name, and virtual bind target.
        """
        self.config = config

    @staticmethod
    def _require_openziti() -> Any:
        """Dynamically load openziti module or raise MissingDependencyError.

        Returns:
            The imported openziti module.

        Raises:
            MissingDependencyError: If openziti is not installed.
        """
        try:
            import openziti

            return openziti
        except ImportError as exc:
            raise MissingDependencyError(
                "openziti is required for OpenZiti zero-trust networking. "
                "Install with 'pip install hexastack-fastapi[ziti]' or 'pip install openziti'."
            ) from exc

    def get_bindings(self) -> dict[tuple[str, int], dict[str, Any]]:
        """Construct the OpenZiti socket binding mapping.

        Returns:
            Dictionary mapping (host, port) to OpenZiti context and service options.

        Raises:
            FileNotFoundError: If the identity credentials file does not exist.
        """
        identity_file = self.config.resolved_identity_path()
        return {
            (self.config.bind_host, self.config.bind_port): {
                "ztx": str(identity_file),
                "service": self.config.service_name,
            }
        }

    @contextlib.contextmanager
    def bind_context(self) -> Generator[None]:
        """Context manager activating OpenZiti overlay socket interception.

        Yields:
            None when socket interception is active.

        Raises:
            MissingDependencyError: If openziti is not installed.
            FileNotFoundError: If the identity file does not exist.

        Notes/Architectural Intent:
            Activates openziti.monkeypatch with configured bindings upon entry,
            restoring original Python socket behaviors upon exit.
        """
        if not self.config.enabled:
            yield
            return

        openziti = self._require_openziti()
        bindings = self.get_bindings()
        with openziti.monkeypatch(bindings=bindings):
            yield

    def zitify(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Decorate a server runner function to execute within the OpenZiti overlay.

        Args:
            func: Target callable to decorate (e.g. uvicorn.run or server startup).

        Returns:
            Decorated callable wrapped with OpenZiti overlay socket interception.
        """

        def wrapped(*args: Any, **kwargs: Any) -> Any:
            with self.bind_context():
                return func(*args, **kwargs)

        return wrapped

    @staticmethod
    def _require_uvicorn() -> Any:
        """Dynamically load uvicorn module or raise MissingDependencyError.

        Returns:
            The imported uvicorn module.

        Raises:
            MissingDependencyError: If uvicorn is not installed.
        """
        try:
            import uvicorn

            return uvicorn
        except ImportError as exc:
            raise MissingDependencyError(
                "uvicorn is required to run the ASGI server. "
                "Install with 'pip install uvicorn[standard]'."
            ) from exc

    def run_uvicorn(self, app: Any, **uvicorn_kwargs: Any) -> None:
        """Launch Uvicorn to serve the ASGI application over the OpenZiti overlay.

        Args:
            app: The FastAPI, Starlette, or ASGI application instance or import string.
            **uvicorn_kwargs: Additional keyword arguments passed to uvicorn.run.

        Raises:
            MissingDependencyError: If openziti or uvicorn is not installed.
            FileNotFoundError: If the identity file does not exist.
        """
        uvicorn = self._require_uvicorn()
        host = uvicorn_kwargs.pop("host", self.config.bind_host)
        port = uvicorn_kwargs.pop("port", self.config.bind_port)

        with self.bind_context():
            uvicorn.run(app, host=host, port=port, **uvicorn_kwargs)


def openziti_bind(
    identity_path: Path | str,
    service_name: str,
    bind_host: str = "127.0.0.1",
    bind_port: int = 8000,
) -> contextlib.AbstractContextManager[None]:
    """Convenience context manager to bind current process sockets to an OpenZiti service.

    Args:
        identity_path: Path to the enrolled OpenZiti identity credentials file.
        service_name: Name of the OpenZiti service to host.
        bind_host: Virtual bind host address. Defaults to '127.0.0.1'.
        bind_port: Virtual bind port number. Defaults to 8000.

    Returns:
        Context manager that intercepts socket operations for the given host and port.
    """
    config = OpenZitiConfig(
        identity_path=identity_path,
        service_name=service_name,
        bind_host=bind_host,
        bind_port=bind_port,
    )
    adapter = OpenZitiASGIAdapter(config)
    return adapter.bind_context()
