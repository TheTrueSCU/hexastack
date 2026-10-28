"""ASGI HTTP server runners supporting Uvicorn and Rust-backed Granian engines.

Notes/Architectural Intent:
    Decouples ASGI application serving from a specific server engine, enabling zero-configuration
    switching between standard Uvicorn and ultra-high-throughput Rust-backed Granian.
"""

from __future__ import annotations

import os
from typing import Any, Literal

from hexastack_core.utils.imports import require_dependency

ServerEngine = Literal["uvicorn", "granian"]

__all__ = [
    "run_granian",
    "run_server",
    "run_uvicorn",
    "ServerEngine",
]


def run_uvicorn(
    app: Any,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    workers: int | None = None,
    factory: bool = False,
    log_access: bool = True,
    **kwargs: Any,
) -> None:
    """Run an ASGI application using Uvicorn.

    Args:
        app: ASGI application instance or import target string.
        host: Bind host address (defaults to '127.0.0.1').
        port: Bind port number (defaults to 8000).
        reload: Whether to enable auto-reload on filesystem changes.
        workers: Number of worker processes (ignored if reload is True in Uvicorn).
        factory: Whether app is a factory callable returning an ASGI application.
        log_access: Whether to enable access logs.
        **kwargs: Additional keyword arguments passed to uvicorn.run.

    Raises:
        MissingDependencyError: If uvicorn is not installed.
    """
    uvicorn = require_dependency(
        "uvicorn",
        extra="fastapi",
        package="hexastack-fastapi",
        feature_name="run_uvicorn",
    )
    run_kwargs: dict[str, Any] = {
        "host": host,
        "port": port,
        "reload": reload,
        "factory": factory,
        "access_log": log_access,
        **kwargs,
    }
    if workers is not None and not reload:
        run_kwargs["workers"] = workers

    uvicorn.run(app, **run_kwargs)


def run_granian(
    app: Any,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    workers: int | None = None,
    factory: bool = False,
    log_access: bool = True,
    **kwargs: Any,
) -> None:
    """Run an ASGI application using the Rust-backed Granian engine.

    Args:
        app: ASGI application instance or import target string.
        host: Bind host address (defaults to '127.0.0.1').
        port: Bind port number (defaults to 8000).
        reload: Whether to enable auto-reload on filesystem changes.
        workers: Number of worker processes (defaults to CPU core count or 1).
        factory: Whether app is a factory callable returning an ASGI application.
        log_access: Whether to enable access logs.
        **kwargs: Additional keyword arguments passed to Granian.

    Raises:
        MissingDependencyError: If granian is not installed.

    Notes/Architectural Intent:
        Granian leverages a high-performance Rust core (built on Hyper and Tokio)
        to deliver significantly lower request latencies and higher concurrency throughput
        compared to pure-Python event loops.
    """
    granian_mod = require_dependency(
        "granian",
        extra="granian",
        package="hexastack-fastapi",
        feature_name="run_granian",
    )
    from granian.constants import Interfaces

    worker_count = workers if workers is not None else max(1, os.cpu_count() or 1)

    server = granian_mod.Granian(
        app,
        address=host,
        port=port,
        interface=Interfaces.ASGI,
        workers=worker_count if not reload else 1,
        reload=reload,
        factory=factory,
        log_access=log_access,
        **kwargs,
    )
    server.serve()


def run_server(
    app: Any,
    *,
    engine: ServerEngine | str = "uvicorn",
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = False,
    workers: int | None = None,
    factory: bool = False,
    log_access: bool = True,
    **extra_kwargs: Any,
) -> None:
    """Run an ASGI application dispatching to the configured HTTP server engine.

    Args:
        app: ASGI application instance or import target string.
        engine: HTTP server engine ('uvicorn' or 'granian', defaults to 'uvicorn').
        host: Bind host address.
        port: Bind port number.
        reload: Whether to enable auto-reload.
        workers: Number of worker processes.
        factory: Whether app is a factory callable.
        log_access: Whether to enable access logs.
        **extra_kwargs: Extra keyword arguments forwarded to the underlying engine runner.

    Raises:
        ValueError: If an unsupported engine is specified.
        MissingDependencyError: If the chosen engine is not installed.
    """
    engine_name = engine.lower().strip()
    if engine_name == "uvicorn":
        run_uvicorn(
            app,
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            factory=factory,
            log_access=log_access,
            **extra_kwargs,
        )
    elif engine_name == "granian":
        run_granian(
            app,
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            factory=factory,
            log_access=log_access,
            **extra_kwargs,
        )
    else:
        raise ValueError(
            f"Unsupported server engine '{engine}'. Supported engines: 'uvicorn', 'granian'."
        )
