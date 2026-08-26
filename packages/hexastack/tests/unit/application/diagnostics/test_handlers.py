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
