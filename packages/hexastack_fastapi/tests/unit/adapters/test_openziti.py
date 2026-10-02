"""Unit tests for OpenZiti zero-trust ASGI presentation adapter.

Notes/Architectural Intent:
    Verifies that OpenZiti configuration resolution, dependency detection,
    monkeypatch socket binding interception, and Uvicorn orchestration behave
    deterministically across all edge cases without requiring live network overlay connections.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_fastapi.adapters.openziti import (
    OpenZitiASGIAdapter,
    OpenZitiConfig,
    openziti_bind,
)


def test_openziti_config_resolution_success(tmp_path: Path) -> None:
    """Verify that a valid identity file path resolves correctly."""
    identity_file = tmp_path / "ziti_id.json"
    identity_file.write_text('{"ztx": "test"}', encoding="utf-8")

    config = OpenZitiConfig(
        identity_path=identity_file,
        service_name="dark-microservice",
        bind_host="127.0.0.1",
        bind_port=9000,
    )

    resolved = config.resolved_identity_path()
    assert resolved == identity_file.resolve()
    assert config.service_name == "dark-microservice"
    assert config.bind_host == "127.0.0.1"
    assert config.bind_port == 9000
    assert config.enabled is True


def test_openziti_config_resolution_missing_file(tmp_path: Path) -> None:
    """Verify that a non-existent identity file raises FileNotFoundError."""
    missing_file = tmp_path / "non_existent.json"
    config = OpenZitiConfig(
        identity_path=missing_file,
        service_name="dark-microservice",
    )

    with pytest.raises(
        FileNotFoundError, match="OpenZiti identity credentials file not found"
    ):
        config.resolved_identity_path()


def test_openziti_adapter_missing_dependency(tmp_path: Path) -> None:
    """Verify that MissingDependencyError is raised when openziti is not installed."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")
    config = OpenZitiConfig(identity_path=identity_file, service_name="dark-svc")
    adapter = OpenZitiASGIAdapter(config)

    with (
        patch.object(
            OpenZitiASGIAdapter,
            "_require_openziti",
            side_effect=MissingDependencyError(
                "openziti is required for OpenZiti zero-trust networking."
            ),
        ),
        pytest.raises(MissingDependencyError, match="openziti is required"),
        adapter.bind_context(),
    ):
        pass


def test_openziti_adapter_get_bindings(tmp_path: Path) -> None:
    """Verify that socket binding mappings match the configured host, port, and identity."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")
    config = OpenZitiConfig(
        identity_path=identity_file,
        service_name="my-service",
        bind_host="0.0.0.0",
        bind_port=8443,
    )
    adapter = OpenZitiASGIAdapter(config)

    bindings = adapter.get_bindings()
    expected_key = ("0.0.0.0", 8443)
    assert expected_key in bindings
    assert bindings[expected_key]["service"] == "my-service"
    assert bindings[expected_key]["ztx"] == str(identity_file.resolve())


def test_openziti_adapter_bind_context_disabled(tmp_path: Path) -> None:
    """Verify that when disabled, bind_context does not trigger openziti monkeypatch."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")
    config = OpenZitiConfig(
        identity_path=identity_file,
        service_name="my-service",
        enabled=False,
    )
    adapter = OpenZitiASGIAdapter(config)

    mock_openziti = MagicMock()
    with patch.object(
        OpenZitiASGIAdapter, "_require_openziti", return_value=mock_openziti
    ):
        executed = False
        with adapter.bind_context():
            executed = True

        assert executed is True
        mock_openziti.monkeypatch.assert_not_called()


def test_openziti_adapter_bind_context_enabled(tmp_path: Path) -> None:
    """Verify that when enabled, bind_context activates openziti.monkeypatch with correct bindings."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")
    config = OpenZitiConfig(
        identity_path=identity_file,
        service_name="secure-api",
        bind_host="127.0.0.1",
        bind_port=8080,
    )
    adapter = OpenZitiASGIAdapter(config)

    mock_patch_cm = MagicMock()
    mock_openziti = MagicMock()
    mock_openziti.monkeypatch.return_value = mock_patch_cm

    with (
        patch.object(
            OpenZitiASGIAdapter, "_require_openziti", return_value=mock_openziti
        ),
        adapter.bind_context(),
    ):
        mock_openziti.monkeypatch.assert_called_once_with(
            bindings=adapter.get_bindings()
        )
        mock_patch_cm.__enter__.assert_called_once()

    mock_patch_cm.__exit__.assert_called_once()


def test_openziti_adapter_zitify_decorator(tmp_path: Path) -> None:
    """Verify that zitify decorator executes functions within the bind_context."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")
    config = OpenZitiConfig(
        identity_path=identity_file,
        service_name="decorated-service",
    )
    adapter = OpenZitiASGIAdapter(config)

    mock_openziti = MagicMock()
    with patch.object(
        OpenZitiASGIAdapter, "_require_openziti", return_value=mock_openziti
    ):

        @adapter.zitify
        def sample_server(val: int) -> int:
            return val * 2

        res = sample_server(21)
        assert res == 42
        mock_openziti.monkeypatch.assert_called_once()


def test_openziti_adapter_run_uvicorn_missing_uvicorn(tmp_path: Path) -> None:
    """Verify that MissingDependencyError is raised when uvicorn is not installed."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")
    config = OpenZitiConfig(identity_path=identity_file, service_name="dark-svc")
    adapter = OpenZitiASGIAdapter(config)

    with (
        patch.object(
            OpenZitiASGIAdapter,
            "_require_uvicorn",
            side_effect=MissingDependencyError(
                "uvicorn is required to run the ASGI server."
            ),
        ),
        pytest.raises(MissingDependencyError, match="uvicorn is required"),
    ):
        adapter.run_uvicorn("mock.app:app")


def test_openziti_adapter_run_uvicorn_success(tmp_path: Path) -> None:
    """Verify that run_uvicorn launches uvicorn inside the openziti bind context."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")
    config = OpenZitiConfig(
        identity_path=identity_file,
        service_name="api-service",
        bind_host="0.0.0.0",
        bind_port=5000,
    )
    adapter = OpenZitiASGIAdapter(config)

    mock_openziti = MagicMock()
    mock_uvicorn = MagicMock()

    with (
        patch.object(
            OpenZitiASGIAdapter, "_require_openziti", return_value=mock_openziti
        ),
        patch.object(
            OpenZitiASGIAdapter, "_require_uvicorn", return_value=mock_uvicorn
        ),
    ):
        adapter.run_uvicorn("test:app", reload=True, workers=4)

        mock_uvicorn.run.assert_called_once_with(
            "test:app",
            host="0.0.0.0",
            port=5000,
            reload=True,
            workers=4,
        )


def test_openziti_bind_convenience_function(tmp_path: Path) -> None:
    """Verify that openziti_bind convenience function constructs adapter and yields context."""
    identity_file = tmp_path / "id.json"
    identity_file.write_text("{}", encoding="utf-8")

    mock_openziti = MagicMock()
    with (
        patch.object(
            OpenZitiASGIAdapter, "_require_openziti", return_value=mock_openziti
        ),
        openziti_bind(
            identity_file, "fastapi-dark-svc", bind_host="127.0.0.1", bind_port=8000
        ),
    ):
        mock_openziti.monkeypatch.assert_called_once()
