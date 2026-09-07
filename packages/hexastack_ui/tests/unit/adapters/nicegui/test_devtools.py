"""Unit tests for NiceGUI DevTools dashboard."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from rodi import Container
from starlette.routing import Mount

from hexastack_core.domain import Command
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_ui.adapters.nicegui.devtools import mount_devtools_dashboard


def test_mount_devtools_dashboard():
    """Verify mount_devtools_dashboard attaches to FastAPI app and page renders."""
    from nicegui import core

    app = FastAPI()
    container = Container()
    pipeline = MagicMock(spec=ExecutionPipeline)

    mount_devtools_dashboard(
        app, container=container, pipeline=pipeline, path="/_devtools"
    )

    assert any(isinstance(r, Mount) for r in app.routes)
    assert len(core.app.routes) > 0


def test_render_internal_tabs():
    """Verify internal rendering helpers execute cleanly across container states."""
    from nicegui import Client
    from nicegui.page import page

    from hexastack_core.adapters.feature_flags.in_memory import (
        InMemoryFeatureFlagAdapter,
    )
    from hexastack_core.ports.feature_flags import FeatureFlagPort
    from hexastack_cqrs.infra.middleware.correlation import CorrelationMiddleware
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_cqrs.infra.registries.query import QueryRegistry
    from hexastack_cqrs.ports.buses import CommandBusPort
    from hexastack_ui.adapters.nicegui.devtools import (
        _render_container_tab,
        _render_cqrs_messages,
        _render_cqrs_tab,
        _render_flags_tab,
        _render_live_runner,
        _render_middleware_chain,
    )

    client = Client(page("/test-render-tabs"))
    with client.layout.default_slot:
        empty_container = Container()
        _render_cqrs_messages(empty_container)
        _render_middleware_chain([])
        _render_live_runner(empty_container, None, [])
        _render_cqrs_tab(empty_container, None)
        _render_flags_tab(empty_container)
        _render_container_tab(empty_container)

        container = Container()
        cmd_reg = CommandRegistry()
        qry_reg = QueryRegistry()
        from hexastack_core.domain.command import Command as BaseCmd
        from hexastack_core.domain.query import Query as BaseQry

        class PlainCmd(BaseCmd):
            pass

        class PlainQry(BaseQry):
            pass

        cmd_reg.register(PlainCmd)
        qry_reg.register(PlainQry)

        container.add_instance(cmd_reg, declared_class=CommandRegistry)
        container.add_instance(qry_reg, declared_class=QueryRegistry)

        flags_adapter = InMemoryFeatureFlagAdapter({"beta_feature": True, "limit": 100})
        container.add_instance(flags_adapter, declared_class=FeatureFlagPort)

        cmd_bus_mock = MagicMock()
        mw = CorrelationMiddleware()
        cmd_bus_mock._middleware = [mw]
        container.add_instance(cmd_bus_mock, declared_class=CommandBusPort)

        pipeline_mock = MagicMock(spec=ExecutionPipeline)
        pipeline_mock.execute = MagicMock(return_value="executed-ok")

        class AuthTestMiddleware:
            pass

        _render_cqrs_messages(container)
        _render_middleware_chain([mw, AuthTestMiddleware()])
        _render_live_runner(container, pipeline_mock, [mw])
        _render_cqrs_tab(container, pipeline=pipeline_mock)
        _render_flags_tab(container)
        _render_container_tab(container)


def _find_button_and_click(element):
    """Helper to find button with text 'Dispatch Ping Command' recursively."""
    if getattr(element, "text", "") == "Dispatch Ping Command":
        return element._props.get("on_click")
    slot = getattr(element, "default_slot", None)
    children = getattr(slot, "children", []) if slot is not None else []
    for child in children:
        handler = _find_button_and_click(child)
        if handler:
            return handler
    return None


@pytest.mark.anyio
async def test_dispatch_ping_direct():
    """Verify _dispatch_ping handles all resolution branches directly."""
    from hexastack_cqrs.infra.registries.command import CommandRegistry
    from hexastack_ui.adapters.nicegui.devtools import _dispatch_ping

    log_output = MagicMock()

    # 1. Pipeline + Registered Ping command
    container = Container()
    creg = CommandRegistry()

    @dataclass(frozen=True)
    class PingDemoCommand(Command):
        message: str = ""

    creg.register(PingDemoCommand)
    container.add_instance(creg, declared_class=CommandRegistry)

    pipeline = MagicMock(spec=ExecutionPipeline)
    pipeline.execute = MagicMock(return_value="PONG: Direct")
    container.add_instance(pipeline, declared_class=ExecutionPipeline)

    await _dispatch_ping("hello", container, None, ["MockMW"], log_output)
    pipeline.execute.assert_called_once()

    # 2. Pipeline directly passed, no registered command -> execute_by_name
    pipeline_direct = MagicMock(spec=ExecutionPipeline)
    pipeline_direct.execute_by_name = MagicMock(return_value="PONG: DirectName")
    await _dispatch_ping("hello", Container(), pipeline_direct, [], log_output)
    pipeline_direct.execute_by_name.assert_called_once()

    # 3. No pipeline
    await _dispatch_ping("hello", Container(), None, [], log_output)


def test_render_devtools_content():
    """Verify _render_devtools_content builds all tabs and header."""
    from nicegui import Client
    from nicegui.page import page

    from hexastack_ui.adapters.nicegui.devtools import _render_devtools_content

    container = Container()
    pipeline = MagicMock(spec=ExecutionPipeline)

    client = Client(page("/test-devtools-full"))
    with client.content:
        _render_devtools_content(container, pipeline, "Hexastack DevTools Full Test")
