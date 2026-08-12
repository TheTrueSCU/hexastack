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
    assert "fastapi" in result.optional_dependencies
    assert "huey" in result.optional_dependencies
    assert "pydantic" not in result.optional_dependencies
    assert "rodi" not in result.optional_dependencies


def test_inspect_registry_handler():
    handler_reg = HandlerRegistry()
    handler_reg.register(PingDemoCommand, lambda cmd: None)
    config_reg = ConfigRegistry()

    handler = InspectRegistryHandler(
        handler_registry=handler_reg, config_registry=config_reg
    )
    result = handler(InspectRegistryQuery())
    assert "PingDemoCommand" in result.commands


def test_ping_demo_handler():
    set_correlation_id("test-corr-456")
    handler = PingDemoHandler()
    res = handler(PingDemoCommand(message="hexastack-ping"))
    assert res.reply == "PONG: hexastack-ping"
    assert res.correlation_id == "test-corr-456"
