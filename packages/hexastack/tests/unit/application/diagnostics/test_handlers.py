import pytest
from inline_snapshot import snapshot

from hexastack.application.diagnostics import (
    GetSystemInfoHandler,
    InspectRegistryHandler,
    PingDemoHandler,
)
from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    InspectRegistryQuery,
    PingDemoCommand,
)
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.utils.context import set_correlation_id
from hexastack_cqrs.infra.registries.handler import HandlerRegistry


def test_get_system_info_handler():
    handler = GetSystemInfoHandler()
    result = handler(GetSystemInfoQuery())
    assert result.python_version is not None
    assert result.platform is not None
    assert "hexastack-core" in result.installed_packages
    assert "hexastack-events" in result.installed_packages
    assert "hexastack-fastapi" in result.installed_packages

    # Fastapi is installed, so fastapi and pydantic are in required_dependencies
    assert (
        "fastapi" in result.required_dependencies
        or "fastapi" in result.optional_dependencies
    )
    assert isinstance(result.required_dependencies, dict)
    assert isinstance(result.optional_dependencies, dict)
    assert isinstance(result.extras, dict)


@pytest.mark.snapshot
def test_inspect_registry_handler():
    handler_reg = HandlerRegistry()
    handler_reg.register(PingDemoCommand, lambda cmd: None)
    config_reg = ConfigRegistry()

    handler = InspectRegistryHandler(
        handler_registry=handler_reg, config_registry=config_reg
    )
    result = handler(InspectRegistryQuery())
    assert result.commands == snapshot(["PingDemoCommand"])
    assert result.queries == snapshot([])
    assert result.configs == snapshot([])


@pytest.mark.snapshot
def test_ping_demo_handler(fake_user_id: str):
    set_correlation_id("test-corr-456")
    handler = PingDemoHandler()
    msg = f"hello-{fake_user_id}"
    res = handler(PingDemoCommand(message=msg))
    assert res.reply == f"PONG: hello-{fake_user_id}"
    assert res.correlation_id == snapshot("test-corr-456")


def test_diagnostics_helpers_and_error_handling(tmp_path, monkeypatch):
    """Verify diagnostics helpers covering uninstalled packages and malformed pyproject."""
    from hexastack.application.diagnostics.handlers import (
        _discover_installed_hexastack,
        _evaluate_extras_status,
        _is_module_available,
        _parse_pyproject_metadata,
    )

    # 1. Uninstalled package handling
    installed_map, names = _discover_installed_hexastack(["hexastack-nonexistent-xyz"])
    assert installed_map["hexastack-nonexistent-xyz"] == "not installed"

    # 2. Module availability check
    assert _is_module_available("hexastack_core") is True
    assert _is_module_available("nonexistent_package_12345") is False

    # 3. Extras evaluation
    status = _evaluate_extras_status({"core": ["hexastack-core"], "fake": ["fake-pkg"]})
    assert isinstance(status, dict)

    # 4. Malformed pyproject handling
    bad_toml = tmp_path / "pyproject.toml"
    bad_toml.write_text("invalid [[ toml format ::::")
    monkeypatch.setattr(
        "hexastack.application.diagnostics.handlers._find_pyproject_toml",
        lambda: bad_toml,
    )
    packages, extras = _parse_pyproject_metadata()
    assert len(packages) > 0

    # 5. Missing pyproject handling
    monkeypatch.setattr(
        "hexastack.application.diagnostics.handlers._find_pyproject_toml", lambda: None
    )
    packages_empty, extras_empty = _parse_pyproject_metadata()
    assert len(packages_empty) > 0
