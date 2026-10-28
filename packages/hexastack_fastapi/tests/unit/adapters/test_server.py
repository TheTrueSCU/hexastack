"""Unit tests for ASGI HTTP server runners (Uvicorn and Granian).

Notes/Architectural Intent:
    Verifies that the server adapter cleanly delegates to Uvicorn or Granian
    based on engine configuration, validates worker tuning, and properly raises
    MissingDependencyError when required extras are absent. Uses ephemeral free ports
    via find_free_port() to guarantee safe parallel execution across xdist workers.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_fastapi.adapters.server import (
    run_granian,
    run_server,
    run_uvicorn,
)
from hexastack_fastapi.testing.server import find_free_port


def test_run_uvicorn_delegates_to_uvicorn() -> None:
    """Verify run_uvicorn calls uvicorn.run with mapped parameters and free port."""
    mock_uvicorn = MagicMock()
    port = find_free_port()

    with patch(
        "hexastack_fastapi.adapters.server.require_dependency",
        return_value=mock_uvicorn,
    ):
        run_uvicorn(
            "app.main:app",
            host="127.0.0.1",
            port=port,
            reload=False,
            workers=4,
            factory=True,
            log_access=False,
        )

    mock_uvicorn.run.assert_called_once_with(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        factory=True,
        access_log=False,
        workers=4,
    )


def test_run_uvicorn_missing_dependency() -> None:
    """Verify run_uvicorn raises MissingDependencyError when uvicorn is missing."""
    with (
        patch(
            "hexastack_fastapi.adapters.server.require_dependency",
            side_effect=MissingDependencyError("uvicorn missing"),
        ),
        pytest.raises(MissingDependencyError, match="uvicorn missing"),
    ):
        run_uvicorn("app:app")


def test_run_granian_delegates_to_granian() -> None:
    """Verify run_granian configures and starts Granian server with free port."""
    mock_granian_mod = MagicMock()
    mock_server = MagicMock()
    mock_granian_mod.Granian.return_value = mock_server
    port = find_free_port()

    with patch(
        "hexastack_fastapi.adapters.server.require_dependency",
        return_value=mock_granian_mod,
    ):
        run_granian(
            "app.main:create_app",
            host="127.0.0.1",
            port=port,
            reload=False,
            workers=2,
            factory=True,
            log_access=True,
        )

    mock_granian_mod.Granian.assert_called_once()
    call_kwargs = mock_granian_mod.Granian.call_args[1]
    assert call_kwargs["address"] == "127.0.0.1"
    assert call_kwargs["port"] == port
    assert call_kwargs["workers"] == 2
    assert call_kwargs["factory"] is True
    assert call_kwargs["log_access"] is True
    mock_server.serve.assert_called_once()


def test_run_granian_single_worker_on_reload() -> None:
    """Verify run_granian enforces workers=1 when reload is enabled."""
    mock_granian_mod = MagicMock()
    mock_server = MagicMock()
    mock_granian_mod.Granian.return_value = mock_server
    port = find_free_port()

    with patch(
        "hexastack_fastapi.adapters.server.require_dependency",
        return_value=mock_granian_mod,
    ):
        run_granian(
            "app.main:create_app",
            port=port,
            reload=True,
            workers=8,
        )

    call_kwargs = mock_granian_mod.Granian.call_args[1]
    assert call_kwargs["workers"] == 1
    assert call_kwargs["reload"] is True


def test_run_granian_missing_dependency() -> None:
    """Verify run_granian raises MissingDependencyError when granian is missing."""
    with (
        patch(
            "hexastack_fastapi.adapters.server.require_dependency",
            side_effect=MissingDependencyError("granian missing"),
        ),
        pytest.raises(MissingDependencyError, match="granian missing"),
    ):
        run_granian("app:app")


def test_run_server_dispatch_uvicorn() -> None:
    """Verify run_server dispatches to run_uvicorn for 'uvicorn' engine."""
    port = find_free_port()
    with patch("hexastack_fastapi.adapters.server.run_uvicorn") as mock_run:
        run_server("app:app", engine="Uvicorn", host="127.0.0.1", port=port)
        mock_run.assert_called_once_with(
            "app:app",
            host="127.0.0.1",
            port=port,
            reload=False,
            workers=None,
            factory=False,
            log_access=True,
        )


def test_run_server_dispatch_granian() -> None:
    """Verify run_server dispatches to run_granian for 'granian' engine."""
    port = find_free_port()
    with patch("hexastack_fastapi.adapters.server.run_granian") as mock_run:
        run_server("app:app", engine="GRANIAN", host="127.0.0.1", port=port)
        mock_run.assert_called_once_with(
            "app:app",
            host="127.0.0.1",
            port=port,
            reload=False,
            workers=None,
            factory=False,
            log_access=True,
        )


def test_run_server_unsupported_engine() -> None:
    """Verify run_server raises ValueError for unsupported engine name."""
    with pytest.raises(ValueError, match="Unsupported server engine 'gunicorn'"):
        run_server("app:app", engine="gunicorn")
